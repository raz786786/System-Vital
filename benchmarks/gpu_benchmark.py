"""
SYSTEM VITAL GPU BENCHMARK ENGINE
Industry-level GPU tests using ModernGL (OpenGL) + NumPy:
  - Basic:
    - Vertex Throughput (geometry processing)
    - Fragment Throughput (pixel fill rate)
    - Mandelbrot Fractal (compute-heavy fragment shader)
    - Texture Sampling Throughput
    - Compute Shader GFLOPS (via ModernGL compute)
    - GPU Memory Bandwidth (via PBO transfers)
    - Particle Physics Simulation (vertex shader compute)
  - Extended:
    - Ray Marching / Sphere Tracing
    - Depth of Field (Bokeh Blur)
    - Shadow Map Rendering
    - Ambient Occlusion (SSAO)
    - Gaussian Blur (Multi-Pass)
    - Normal Mapping + Parallax
    - GPU Compute: N-Body Gravity
    - Perlin Noise Terrain
    - HDR Tone Mapping (ACES)
    - Full Deferred Rendering Pass

All rendering is done off-screen (no visible window required).
"""

import time
import math
import struct
import threading
import numpy as np
from typing import Callable, Optional

try:
    import moderngl
    MODERNGL_AVAILABLE = True
except ImportError:
    MODERNGL_AVAILABLE = False

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
#  BASIC SHADERS
# ══════════════════════════════════════════════════════════════

VERT_PASSTHROUGH = """
#version 330 core
in vec2 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

FRAG_MANDELBROT = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform int u_max_iter;
uniform float u_zoom;
uniform vec2 u_center;

void main() {
    vec2 c = (v_uv - 0.5) * u_zoom + u_center;
    vec2 z = vec2(0.0);
    int iter = 0;
    for (int i = 0; i < u_max_iter; i++) {
        if (dot(z, z) > 4.0) break;
        z = vec2(z.x*z.x - z.y*z.y + c.x,
                 2.0*z.x*z.y          + c.y);
        iter++;
    }
    float t = float(iter) / float(u_max_iter);
    float r = t * t;
    float g = t;
    float b = sqrt(t);
    fragColor = vec4(r, g, b, 1.0);
}
"""

FRAG_BLINNPHONG = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform vec3 u_light_pos;
uniform vec3 u_view_pos;
uniform int  u_light_count;

void main() {
    vec2 pos  = v_uv * 2.0 - 1.0;
    float r2  = dot(pos, pos);
    if (r2 > 1.0) { fragColor = vec4(0.0); return; }
    vec3 N    = normalize(vec3(pos, sqrt(1.0 - r2)));
    vec3 V    = normalize(u_view_pos);
    vec3 col  = vec3(0.05);
    for (int i = 0; i < u_light_count; i++) {
        float angle = float(i) * 0.628318;
        vec3 L      = normalize(vec3(cos(angle), sin(angle), 0.8));
        vec3 H      = normalize(L + V);
        float diff  = max(dot(N, L), 0.0);
        float spec  = pow(max(dot(N, H), 0.0), 64.0);
        col        += vec3(0.2) * diff + vec3(0.5) * spec;
    }
    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""

FRAG_TEXTURE_STRESS = """
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
uniform sampler2D u_tex;
uniform int       u_taps;

void main() {
    vec4 acc = vec4(0.0);
    vec2 uv = v_uv;
    for (int i = 0; i < u_taps; i++) {
        acc += texture(u_tex, uv);
        uv  = fract(uv * 1.618 + acc.rg * 0.001);
    }
    fragColor = acc / float(u_taps);
}
"""

# ══════════════════════════════════════════════════════════════
#  EXTENDED SHADERS
# ══════════════════════════════════════════════════════════════

VERT_FULLSCREEN = """
#version 330 core
in  vec2 in_vert;
out vec2 v_uv;
out vec2 v_ndc;
void main() {
    v_uv        = in_vert * 0.5 + 0.5;
    v_ndc       = in_vert;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

VERT_3D = """
#version 330 core
in  vec3 in_position;
in  vec3 in_normal;
in  vec2 in_uv;
out vec3 v_pos;
out vec3 v_normal;
out vec2 v_uv;
uniform mat4 u_mvp;
uniform mat4 u_model;
uniform mat3 u_normal_mat;
void main() {
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    v_pos          = world_pos.xyz;
    v_normal       = normalize(u_normal_mat * in_normal);
    v_uv           = in_uv;
    gl_Position    = u_mvp * vec4(in_position, 1.0);
}
"""

FRAG_RAY_MARCH = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform float u_time;
uniform vec2  u_resolution;

float sdSphere(vec3 p, float r) { return length(p) - r; }
float sdBox(vec3 p, vec3 b) {
    vec3 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, max(d.y, d.z)), 0.0);
}
float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}
float opUnion(float a, float b)    { return min(a, b); }
float opSmoothUnion(float a, float b, float k) {
    float h = clamp(0.5 + 0.5*(b-a)/k, 0.0, 1.0);
    return mix(b, a, h) - k*h*(1.0-h);
}

float sceneSDF(vec3 p) {
    float t    = u_time * 0.5;
    vec3  p1   = p - vec3(sin(t)*1.5, cos(t*1.3)*0.5, 0.0);
    vec3  p2   = p - vec3(cos(t)*1.5, sin(t*0.7)*0.5, sin(t)*1.0);
    vec3  p3   = p - vec3(0.0, cos(t)*1.5, sin(t*1.1)*1.0);

    float s1   = sdSphere(p1, 0.7);
    float s2   = sdSphere(p2, 0.5);
    float s3   = sdTorus(p3, vec2(0.9, 0.25));
    float box  = sdBox(p - vec3(0.0, -2.0, 0.0), vec3(5.0, 0.2, 5.0));

    float blob = opSmoothUnion(opSmoothUnion(s1, s2, 0.5), s3, 0.4);
    return opUnion(blob, box);
}

vec3 calcNormal(vec3 p) {
    const float eps = 0.001;
    return normalize(vec3(
        sceneSDF(p + vec3(eps,0,0)) - sceneSDF(p - vec3(eps,0,0)),
        sceneSDF(p + vec3(0,eps,0)) - sceneSDF(p - vec3(0,eps,0)),
        sceneSDF(p + vec3(0,0,eps)) - sceneSDF(p - vec3(0,0,eps))
    ));
}

float softShadow(vec3 ro, vec3 rd, float mint, float maxt, float k) {
    float res = 1.0;
    float t   = mint;
    for (int i = 0; i < 32; i++) {
        float h = sceneSDF(ro + rd * t);
        if (h < 0.001) return 0.0;
        res  = min(res, k * h / t);
        t   += clamp(h, 0.02, 0.5);
        if (t > maxt) break;
    }
    return clamp(res, 0.0, 1.0);
}

float calcAO(vec3 pos, vec3 nor) {
    float occ = 0.0;
    float sca = 1.0;
    for (int i = 0; i < 5; i++) {
        float h   = 0.01 + 0.12 * float(i) / 4.0;
        float d   = sceneSDF(pos + h * nor);
        occ      += (h - d) * sca;
        sca      *= 0.95;
    }
    return clamp(1.0 - 3.0 * occ, 0.0, 1.0);
}

void main() {
    vec2  uv    = (v_uv * 2.0 - 1.0) * vec2(u_resolution.x / u_resolution.y, 1.0);
    vec3  ro    = vec3(0.0, 1.0, 4.0);
    vec3  rd    = normalize(vec3(uv, -1.5));

    float t     = 0.0;
    float tmax  = 20.0;
    bool  hit   = false;
    for (int i = 0; i < 128; i++) {
        float d = sceneSDF(ro + rd * t);
        if (d < 0.001) { hit = true; break; }
        if (t > tmax)  { break; }
        t += d;
    }

    vec3 col = vec3(0.05, 0.05, 0.15);
    if (hit) {
        vec3 pos  = ro + rd * t;
        vec3 nor  = calcNormal(pos);
        vec3 lig  = normalize(vec3(1.0, 2.0, 1.5));

        float ao  = calcAO(pos, nor);
        float sha = softShadow(pos, lig, 0.02, 10.0, 8.0);
        float dif = clamp(dot(nor, lig), 0.0, 1.0) * sha;
        float amb = 0.5 + 0.5 * nor.y;
        float spe = pow(clamp(dot(reflect(-lig, nor), -rd), 0.0, 1.0), 32.0);

        vec3 matcol = 0.5 + 0.5 * cos(pos * 2.0 + vec3(0.0, 2.0, 4.0));
        col = matcol * (amb * vec3(0.1,0.15,0.2) + dif * vec3(1.0,0.9,0.7))
            + spe * vec3(0.9,0.85,0.8);
        col *= ao;
        col = mix(col, vec3(0.05,0.05,0.15), clamp(t/tmax, 0.0, 1.0));
    }

    col        = pow(clamp(col, 0.0, 1.0), vec3(0.4545));
    fragColor  = vec4(col, 1.0);
}
"""

FRAG_DOF = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_scene;
uniform float     u_focal_dist;
uniform float     u_aperture;
uniform vec2      u_resolution;

const int SAMPLES = 64;
const float PI    = 3.14159265;

vec4 bokehDOF(vec2 uv) {
    float depth     = length(uv - 0.5) * 2.0;
    float coc       = abs(depth - u_focal_dist) * u_aperture;
    coc             = clamp(coc, 0.0, 0.05);

    vec4  acc       = vec4(0.0);
    float total_w   = 0.0;

    for (int i = 0; i < SAMPLES; i++) {
        float angle  = float(i) * (PI * (3.0 - sqrt(5.0)));
        float radius = sqrt(float(i) / float(SAMPLES));
        vec2  offset = vec2(cos(angle), sin(angle)) * radius * coc;
        float w      = 1.0 / (1.0 + length(offset) * 10.0);
        acc         += texture(u_scene, uv + offset) * w;
        total_w     += w;
    }
    return acc / total_w;
}

void main() {
    fragColor = bokehDOF(v_uv);
}
"""

FRAG_SHADOW = """
#version 330 core
in  vec3 v_pos;
in  vec3 v_normal;
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_shadow_map;
uniform mat4      u_light_vp;
uniform vec3      u_light_dir;
uniform vec3      u_cam_pos;

float PCFShadow(vec4 light_space_pos, float bias) {
    vec3 proj = light_space_pos.xyz / light_space_pos.w;
    proj      = proj * 0.5 + 0.5;

    if (proj.z > 1.0) return 1.0;

    float shadow  = 0.0;
    vec2  texelSz = 1.0 / vec2(2048.0);
    for (int x = -2; x <= 2; x++) {
        for (int y = -2; y <= 2; y++) {
            float pcfDepth = texture(u_shadow_map, proj.xy + vec2(x, y) * texelSz).r;
            shadow += (proj.z - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    return 1.0 - (shadow / 25.0);
}

void main() {
    vec3  N         = normalize(v_normal);
    vec3  L         = normalize(-u_light_dir);
    vec3  V         = normalize(u_cam_pos - v_pos);
    vec3  H         = normalize(L + V);

    float diff      = max(dot(N, L), 0.0);
    float spec      = pow(max(dot(N, H), 0.0), 64.0);

    vec4  light_pos = u_light_vp * vec4(v_pos, 1.0);
    float bias      = max(0.005 * (1.0 - dot(N, L)), 0.001);
    float shadow    = PCFShadow(light_pos, bias);

    float checker   = mod(floor(v_uv.x * 8.0) + floor(v_uv.y * 8.0), 2.0);
    vec3  albedo    = mix(vec3(0.9), vec3(0.1), checker);

    vec3  color     = albedo * (0.1 + shadow * diff) + vec3(1.0) * shadow * spec * 0.5;

    fragColor = vec4(color, 1.0);
}
"""

FRAG_SSAO = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_position;
uniform sampler2D u_normal;
uniform sampler2D u_noise;
uniform vec3      u_samples[64];
uniform mat4      u_projection;
uniform vec2      u_noise_scale;

const float RADIUS = 0.5;
const float BIAS   = 0.025;

void main() {
    vec3 frag_pos  = texture(u_position, v_uv).xyz;
    vec3 normal    = normalize(texture(u_normal,   v_uv).rgb);
    vec3 rand_vec  = normalize(texture(u_noise, v_uv * u_noise_scale).xyz);

    vec3 tangent   = normalize(rand_vec - normal * dot(rand_vec, normal));
    vec3 bitangent = cross(normal, tangent);
    mat3 TBN       = mat3(tangent, bitangent, normal);

    float occlusion = 0.0;
    for (int i = 0; i < 64; i++) {
        vec3 sample_pos = TBN * u_samples[i];
        sample_pos      = frag_pos + sample_pos * RADIUS;

        vec4 offset     = vec4(sample_pos, 1.0);
        offset          = u_projection * offset;
        offset.xyz     /= offset.w;
        offset.xyz      = offset.xyz * 0.5 + 0.5;

        float sampleDepth = texture(u_position, offset.xy).z;
        float rangeCheck  = smoothstep(0.0, 1.0, RADIUS / abs(frag_pos.z - sampleDepth));
        occlusion += (sampleDepth >= sample_pos.z + BIAS ? 1.0 : 0.0) * rangeCheck;
    }

    occlusion  = 1.0 - (occlusion / 64.0);
    fragColor  = vec4(occlusion, occlusion, occlusion, 1.0);
}
"""

FRAG_GAUSSIAN_H = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_tex;
uniform vec2      u_resolution;
uniform float     u_sigma;

float gauss(float x, float sigma) {
    return exp(-(x*x) / (2.0 * sigma * sigma));
}

void main() {
    float texelW = 1.0 / u_resolution.x;
    vec4  acc    = vec4(0.0);
    float total  = 0.0;
    int   radius = int(u_sigma * 3.0);

    for (int i = -radius; i <= radius; i++) {
        float w  = gauss(float(i), u_sigma);
        acc     += texture(u_tex, v_uv + vec2(float(i) * texelW, 0.0)) * w;
        total   += w;
    }
    fragColor = acc / total;
}
"""

FRAG_GAUSSIAN_V = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_tex;
uniform vec2      u_resolution;
uniform float     u_sigma;

float gauss(float x, float sigma) {
    return exp(-(x*x) / (2.0 * sigma * sigma));
}

void main() {
    float texelH = 1.0 / u_resolution.y;
    vec4  acc    = vec4(0.0);
    float total  = 0.0;
    int   radius = int(u_sigma * 3.0);

    for (int i = -radius; i <= radius; i++) {
        float w  = gauss(float(i), u_sigma);
        acc     += texture(u_tex, v_uv + vec2(0.0, float(i) * texelH)) * w;
        total   += w;
    }
    fragColor = acc / total;
}
"""

FRAG_PARALLAX = """
#version 330 core
in  vec3 v_pos;
in  vec3 v_normal;
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_diffuse;
uniform sampler2D u_normal_map;
uniform sampler2D u_height_map;
uniform vec3      u_light_pos;
uniform vec3      u_view_pos;

const float HEIGHT_SCALE  = 0.1;
const int   POM_STEPS     = 32;
const int   POM_REFINE    = 8;

vec2 parallaxMapping(vec2 uv, vec3 viewDir) {
    float layerDepth  = 1.0 / float(POM_STEPS);
    float currDepth   = 0.0;
    vec2  deltaUV     = viewDir.xy * HEIGHT_SCALE / (viewDir.z * float(POM_STEPS));

    vec2  currUV      = uv;
    float currMapDepth = texture(u_height_map, currUV).r;

    for (int i = 0; i < POM_STEPS; i++) {
        if (currDepth >= currMapDepth) break;
        currUV       -= deltaUV;
        currMapDepth  = texture(u_height_map, currUV).r;
        currDepth    += layerDepth;
    }

    vec2 prevUV   = currUV + deltaUV;
    float afterD  = currMapDepth - currDepth;
    float beforeD = texture(u_height_map, prevUV).r - currDepth + layerDepth;
    float weight  = afterD / (afterD - beforeD);
    return mix(currUV, prevUV, weight);
}

void main() {
    vec3 V    = normalize(u_view_pos - v_pos);
    vec2 uv   = parallaxMapping(v_uv, V);

    vec3 nrm  = texture(u_normal_map, uv).rgb * 2.0 - 1.0;
    // Use v_normal to prevent optimization and contribute to TBN
    vec3 N    = normalize(v_normal + nrm * 0.1); 


    vec3 L    = normalize(u_light_pos - v_pos);
    vec3 H    = normalize(L + V);

    vec4 diff_col = texture(u_diffuse, uv);
    float diff    = max(dot(N, L), 0.0);
    float spec    = pow(max(dot(N, H), 0.0), 128.0);

    vec3 col  = diff_col.rgb * (0.1 + diff * 0.9) + vec3(0.5) * spec;
    fragColor = vec4(col, 1.0);
}
"""

FRAG_NBODY = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_positions;
uniform int       u_n_bodies;
uniform float     u_dt;
uniform float     u_softening;

void main() {
    int   idx      = int(v_uv.x * float(u_n_bodies));
    ivec2 texCoord = ivec2(idx, 0);
    vec4  self     = texelFetch(u_positions, texCoord, 0);

    vec2  acc      = vec2(0.0);
    float G        = 0.0001;

    for (int i = 0; i < u_n_bodies; i++) {
        if (i == idx) continue;
        vec4  other = texelFetch(u_positions, ivec2(i, 0), 0);
        vec2  diff  = other.xy - self.xy;
        float dist2 = dot(diff, diff) + u_softening * u_softening;
        float dist  = sqrt(dist2);
        acc        += G * diff / (dist2 * dist);
    }

    vec2 new_vel = self.zw + acc * u_dt;
    vec2 new_pos = self.xy + new_vel * u_dt;

    new_pos = fract(new_pos + 1.0) * 2.0 - 1.0;

    fragColor = vec4(new_pos, new_vel);
}
"""

FRAG_PERLIN = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform float u_time;
uniform int   u_octaves;
uniform float u_scale;

vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}

float smootherstep(float t) {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float perlin(vec2 p) {
    vec2  i = floor(p);
    vec2  f = fract(p);
    float ux = smootherstep(f.x);
    float uy = smootherstep(f.y);

    float v00 = dot(hash2(i + vec2(0,0)), f - vec2(0,0));
    float v10 = dot(hash2(i + vec2(1,0)), f - vec2(1,0));
    float v01 = dot(hash2(i + vec2(0,1)), f - vec2(0,1));
    float v11 = dot(hash2(i + vec2(1,1)), f - vec2(1,1));

    return mix(mix(v00, v10, ux), mix(v01, v11, ux), uy);
}

float fbm(vec2 p) {
    float val   = 0.0;
    float amp   = 0.5;
    float freq  = 1.0;
    for (int i = 0; i < u_octaves; i++) {
        val  += amp * perlin(p * freq);
        amp  *= 0.5;
        freq *= 2.0;
    }
    return val;
}

void main() {
    vec2  p        = v_uv * u_scale + vec2(u_time * 0.05);
    float height   = fbm(p) * 0.5 + 0.5;

    vec3  deepWater  = vec3(0.0,  0.15, 0.4);
    vec3  shallowW   = vec3(0.1,  0.4,  0.8);
    vec3  sand       = vec3(0.85, 0.78, 0.5);
    vec3  grass      = vec3(0.2,  0.6,  0.15);
    vec3  forest     = vec3(0.1,  0.4,  0.05);
    vec3  rock       = vec3(0.55, 0.5,  0.45);
    vec3  snow       = vec3(0.95, 0.95, 1.0);

    vec3 col;
    if      (height < 0.30) col = mix(deepWater,  shallowW, height / 0.30);
    else if (height < 0.38) col = mix(shallowW,   sand,    (height - 0.30) / 0.08);
    else if (height < 0.45) col = mix(sand,        grass,  (height - 0.38) / 0.07);
    else if (height < 0.60) col = mix(grass,       forest, (height - 0.45) / 0.15);
    else if (height < 0.72) col = mix(forest,      rock,   (height - 0.60) / 0.12);
    else if (height < 0.85) col = mix(rock,        snow,   (height - 0.72) / 0.13);
    else                    col = snow;

    float dfdx = fbm(p + vec2(0.01, 0.0)) - height;
    float dfdy = fbm(p + vec2(0.0, 0.01)) - height;
    vec3  N    = normalize(vec3(-dfdx * 10.0, -dfdy * 10.0, 1.0));
    float diff = clamp(dot(N, normalize(vec3(1.0, 0.8, 0.6))), 0.0, 1.0);
    col       *= 0.3 + 0.7 * diff;

    fragColor  = vec4(col, 1.0);
}
"""

FRAG_TONEMAPPING = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_hdr;
uniform float     u_exposure;
uniform int       u_passes;

vec3 aces_filmic(vec3 x) {
    float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return clamp((x*(a*x+b))/(x*(c*x+d)+e), 0.0, 1.0);
}

vec3 reinhard(vec3 x) {
    return x / (1.0 + x);
}

vec3 hable(vec3 x) {
    float A = 0.15, B = 0.50, C = 0.10, D = 0.20, E = 0.02, F = 0.30;
    return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F)) - E/F;
}

vec3 chromaticAberration(sampler2D tex, vec2 uv, float strength) {
    vec2 dir = uv - 0.5;
    float r  = texture(tex, uv + dir * strength * 1.0).r;
    float g  = texture(tex, uv + dir * strength * 0.5).g;
    float b  = texture(tex, uv - dir * strength * 0.5).b;
    return vec3(r, g, b);
}

float filmGrain(vec2 uv, float time) {
    return fract(sin(dot(uv + time, vec2(12.9898, 78.233))) * 43758.5453) * 0.05;
}

float vignette(vec2 uv) {
    uv      *= 1.0 - uv.yx;
    float v  = uv.x * uv.y * 15.0;
    return pow(v, 0.3);
}

void main() {
    vec3 hdr_col = chromaticAberration(u_hdr, v_uv, 0.002);
    hdr_col *= u_exposure;

    vec3 aces_col = aces_filmic(hdr_col);
    vec3 rein_col = reinhard(hdr_col);
    vec3 habl_col = hable(hdr_col * 2.0) / hable(vec3(11.2));

    float t   = v_uv.x;
    vec3  col = mix(mix(aces_col, rein_col, t), habl_col, v_uv.y);

    col  += filmGrain(v_uv, u_exposure);
    col  *= vignette(v_uv);
    col   = pow(col, vec3(1.0 / 2.2));

    fragColor = vec4(col, 1.0);
}
"""

FRAG_GBUFFER = """
#version 330 core
in  vec3 v_pos;
in  vec3 v_normal;
in  vec2 v_uv;

layout (location = 0) out vec4 gPosition;
layout (location = 1) out vec4 gNormal;
layout (location = 2) out vec4 gAlbedoSpec;

void main() {
    gPosition   = vec4(v_pos, 1.0);
    gNormal     = vec4(normalize(v_normal), 0.0);
    float c     = mod(floor(v_uv.x * 16.0) + floor(v_uv.y * 16.0), 2.0);
    gAlbedoSpec = vec4(mix(vec3(0.8,0.2,0.1), vec3(0.1,0.2,0.8), c), 0.5);
}
"""

FRAG_DEFERRED_LIGHTING = """
#version 330 core
in  vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_gPosition;
uniform sampler2D u_gNormal;
uniform sampler2D u_gAlbedoSpec;
uniform vec3      u_lights[32];
uniform vec3      u_light_colors[32];
uniform vec3      u_view_pos;

void main() {
    vec3  frag_pos  = texture(u_gPosition,   v_uv).rgb;
    vec3  normal    = texture(u_gNormal,      v_uv).rgb;
    vec4  albspec   = texture(u_gAlbedoSpec,  v_uv);
    vec3  albedo    = albspec.rgb;
    float specular  = albspec.a;

    vec3 lighting   = albedo * 0.05;
    vec3 viewDir    = normalize(u_view_pos - frag_pos);

    for (int i = 0; i < 32; i++) {
        vec3  L     = u_lights[i] - frag_pos;
        float dist  = length(L);
        L           = L / dist;

        float atten = 1.0 / (1.0 + 0.09 * dist + 0.032 * dist * dist);
        float diff  = max(dot(normal, L), 0.0);
        vec3  H     = normalize(L + viewDir);
        float spec  = pow(max(dot(normal, H), 0.0), 64.0) * specular;

        lighting   += (albedo * diff + vec3(spec)) * u_light_colors[i] * atten;
    }

    fragColor = vec4(lighting, 1.0);
}
"""


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def _perspective(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f   = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    M   = np.zeros((4, 4), dtype=np.float32)
    M[0, 0] =  f / aspect
    M[1, 1] =  f
    M[2, 2] = (far + near) / (near - far)
    M[2, 3] = (2 * far * near) / (near - far)
    M[3, 2] = -1.0
    return M

def _look_at(eye: np.ndarray, center: np.ndarray, up: np.ndarray) -> np.ndarray:
    f  = center - eye;         f  /= np.linalg.norm(f)
    r  = np.cross(f, up);      r  /= np.linalg.norm(r)
    u  = np.cross(r, f)
    M  = np.eye(4, dtype=np.float32)
    M[0, :3] =  r;   M[0, 3] = -np.dot(r, eye)
    M[1, :3] =  u;   M[1, 3] = -np.dot(u, eye)
    M[2, :3] = -f;   M[2, 3] =  np.dot(f, eye)
    return M

def _gen_sphere_mesh(rings: int = 32, sectors: int = 32) -> tuple:
    verts   = []
    indices = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(sectors + 1):
            theta = 2.0 * math.pi * s / sectors
            x  =  math.sin(phi) * math.cos(theta)
            y  =  math.cos(phi)
            z  =  math.sin(phi) * math.sin(theta)
            nx, ny, nz = x, y, z
            u  = s / sectors
            v  = r / rings
            verts.extend([x, y, z, nx, ny, nz, u, v])

    for r in range(rings):
        for s in range(sectors):
            a = r * (sectors + 1) + s
            b = a + sectors + 1
            indices.extend([a, b, a + 1, b, b + 1, a + 1])

    return (np.array(verts, dtype=np.float32), np.array(indices, dtype=np.uint32))


# ══════════════════════════════════════════════════════════════
#  MAIN BENCHMARK CLASS
# ══════════════════════════════════════════════════════════════

class GPUBenchmark:
    """
    Combined industry-level GPU benchmarks.
    Includes both basic metrics and extended AAA rendering techniques.
    """

    WIDTH   = 1920
    HEIGHT  = 1080
    FRAMES  = 200

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda msg, pct: None)
        self.ctx         = None
        self._main_fbo   = None
        self._quad_vbo   = None
        self._fullscreen_verts = None

    # ── CONTEXT SETUP ─────────────────────────────────────────

    def _init_context(self):
        if not MODERNGL_AVAILABLE:
            raise RuntimeError("moderngl not installed. Run: pip install moderngl pygame")
        
        self.ctx = moderngl.create_standalone_context(require=330)
        self._main_fbo = self.ctx.framebuffer(
            color_attachments=[
                self.ctx.texture((self.WIDTH, self.HEIGHT), 4)
            ]
        )
        self._main_fbo.use()
        self._build_fullscreen_quad_basic()
        self._make_quad_extended()

    def _build_fullscreen_quad_basic(self):
        vertices = np.array([
            -1.0,  -1.0,  0.0, 0.0,
             1.0,  -1.0,  1.0, 0.0,
            -1.0,   1.0,  0.0, 1.0,
             1.0,   1.0,  1.0, 1.0,
        ], dtype=np.float32)
        self._fullscreen_verts = self.ctx.buffer(vertices.tobytes())

    def _make_fullscreen_vao(self, program) -> 'moderngl.VertexArray':
        return self.ctx.simple_vertex_array(
            program, self._fullscreen_verts,
            'in_position', 'in_uv'
        )

    def _make_quad_extended(self):
        verts = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype=np.float32)
        self._quad_vbo = self.ctx.buffer(verts.tobytes())

    def _quad_vao(self, prog) -> 'moderngl.VertexArray':
        return self.ctx.simple_vertex_array(
            prog, self._quad_vbo, 'in_vert'
        )

    def _mesh_vao(self, prog, verts: np.ndarray, indices: np.ndarray) -> 'moderngl.VertexArray':
        vbo = self.ctx.buffer(verts.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        attrs = []
        if 'in_position' in prog: attrs.append('in_position')
        if 'in_normal' in prog: attrs.append('in_normal')
        if 'in_uv' in prog: attrs.append('in_uv')
        
        # Build layout string based on what's used
        layout = ""
        if 'in_position' in prog: layout += "3f "
        if 'in_normal' in prog: layout += "3f "
        if 'in_uv' in prog: layout += "2f"
        
        return self.ctx.vertex_array(
            prog,
            [(vbo, layout.strip(), *attrs)],
            index_buffer=ibo
        )

    def _render_loop(self, vao, uniforms: dict, n_frames: int) -> float:
        for name, val in uniforms.items():
            if name in vao.program:
                prog_uni = vao.program[name]
                if isinstance(val, (int,)): prog_uni.value = val
                elif isinstance(val, (float,)): prog_uni.value = val
                elif isinstance(val, tuple): prog_uni.value = val

        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        for _ in range(5): vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        # Force GPU sync via pixel readback
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass

        start = time.perf_counter()
        for _ in range(n_frames): vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        return time.perf_counter() - start

    def _run_loop(self, vao, n_frames: int, mode=None, uniforms: dict = None) -> float:
        if mode is None: mode = moderngl.TRIANGLE_STRIP
        if uniforms: self._set_uniforms(vao.program, uniforms)

        # Warmup + Force Sync
        for _ in range(3): vao.render(mode)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass

        start = time.perf_counter()
        for _ in range(n_frames): vao.render(mode)
        self.ctx.finish()
        # Force Sync: Read back one pixel to ensure GPU is actually done
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        return time.perf_counter() - start

    @staticmethod
    def _set_uniforms(prog, uniforms: dict):
        for name, val in uniforms.items():
            try:
                if name in prog: prog[name].value = val
            except Exception:
                pass


    # ── BASIC TESTS ───────────────────────────────────────────

    def test_mandelbrot(self) -> dict:
        self.progress_cb("GPU: Mandelbrot Compute (FP Throughput)...", 5)
        prog = self.ctx.program(vertex_shader=VERT_PASSTHROUGH, fragment_shader=FRAG_MANDELBROT)
        vao = self._make_fullscreen_vao(prog)
        elapsed = self._render_loop(vao, {'u_max_iter': 512, 'u_zoom': 3.5, 'u_center': (-0.7, 0.0)}, self.FRAMES)
        fps = self.FRAMES / elapsed
        gflops = (512 * 10 * self.WIDTH * self.HEIGHT * self.FRAMES) / elapsed / 1e9
        return {
            "name": "Mandelbrot Fractal (FP Compute)",
            "value": round(fps, 2), "unit": "FPS",
            "gflops": round(gflops, 3), "raw": self.FRAMES, "score": self._normalize(fps, 0, 5000)
        }

    def test_lighting(self) -> dict:
        self.progress_cb("GPU: Multi-Light Blinn-Phong Shading...", 10)
        prog = self.ctx.program(vertex_shader=VERT_PASSTHROUGH, fragment_shader=FRAG_BLINNPHONG)
        vao = self._make_fullscreen_vao(prog)
        elapsed = self._render_loop(vao, {'u_light_pos': (10.0, 10.0, 10.0), 'u_view_pos': (0.0, 0.0, 5.0), 'u_light_count': 32}, self.FRAMES)
        fps = self.FRAMES / elapsed
        return {
            "name": "32-Light Blinn-Phong Shading",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 6000)
        }

    def test_texture_sampling(self) -> dict:
        self.progress_cb("GPU: Texture Sampling Throughput...", 15)
        rng = np.random.default_rng(seed=42)
        tex_data = rng.integers(0, 256, (4096, 4096, 4), dtype=np.uint8)
        texture = self.ctx.texture((4096, 4096), 4, tex_data.tobytes())
        texture.use(0)

        prog = self.ctx.program(vertex_shader=VERT_PASSTHROUGH, fragment_shader=FRAG_TEXTURE_STRESS)
        vao = self._make_fullscreen_vao(prog)
        if 'u_tex' in prog: prog['u_tex'].value = 0
        if 'u_taps' in prog: prog['u_taps'].value = 16

        elapsed = self._render_loop(vao, {}, self.FRAMES)
        fps = self.FRAMES / elapsed
        gtexels_per_sec = (self.WIDTH * self.HEIGHT * 16 * fps) / 1e9
        texture.release()
        return {
            "name": "Texture Sampling Throughput (4K, 16 taps)",
            "value": round(gtexels_per_sec, 3), "unit": "GTex/s",
            "fps": round(fps, 2), "raw": self.FRAMES, "score": self._normalize(gtexels_per_sec, 0, 5000)
        }

    def test_vertex_throughput(self) -> dict:
        self.progress_cb("GPU: Vertex Throughput (Geometry Processing)...", 20)
        N_TRIS = 500_000
        rng = np.random.default_rng(seed=55)
        verts = rng.random((N_TRIS * 3, 4), dtype=np.float32) * 2 - 1
        
        vert_shader_heavy = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_uv;
        out vec2 v_uv;
        uniform float u_time;
        void main() {
            float s = sin(in_position.x * 6.28318 + u_time);
            float c = cos(in_position.y * 6.28318 + u_time);
            vec2 rotated = vec2(in_position.x * c - in_position.y * s, in_position.x * s + in_position.y * c);
            v_uv = in_uv;
            gl_Position = vec4(rotated * 0.001, 0.0, 1.0);
        }
        """
        frag_simple = """
        #version 330 core
        in vec2 v_uv;
        out vec4 fragColor;
        void main() { fragColor = vec4(v_uv, 0.5, 1.0); }
        """

        prog = self.ctx.program(vertex_shader=vert_shader_heavy, fragment_shader=frag_simple)
        vbo = self.ctx.buffer(verts.tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_position', 'in_uv')

        if 'u_time' in prog: prog['u_time'].value = 0.0
        FRAMES = 100
        start = time.perf_counter()
        for i in range(FRAMES):
            if 'u_time' in prog: prog['u_time'].value = float(i) * 0.016
            vao.render(moderngl.TRIANGLES)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        elapsed = time.perf_counter() - start

        fps = FRAMES / elapsed
        verts_per_sec = N_TRIS * 3 * fps
        return {
            "name": "Vertex Throughput (Geometry Processing)",
            "value": round(verts_per_sec / 1e9, 3), "unit": "GVerts/s",
            "fps": round(fps, 2), "raw": FRAMES, "score": self._normalize(verts_per_sec / 1e9, 0, 500)
        }

    def test_gpu_memory_bandwidth(self) -> dict:
        self.progress_cb("GPU: VRAM Bandwidth (PBO Transfer)...", 25)
        WIDTH, HEIGHT = 3840, 2160
        SIZE = WIDTH * HEIGHT * 4
        rng = np.random.default_rng(seed=77)
        tex_data = rng.integers(0, 256, (HEIGHT, WIDTH, 4), dtype=np.uint8)
        
        fbo = self.ctx.simple_framebuffer((WIDTH, HEIGHT))
        fbo.use()
        tex = self.ctx.texture((WIDTH, HEIGHT), 4, tex_data.tobytes())

        PASSES = 50
        prog = self.ctx.program(
            vertex_shader=VERT_PASSTHROUGH,
            fragment_shader="#version 330 core\nin vec2 v_uv;\nuniform sampler2D u_tex;\nout vec4 fragColor;\nvoid main() { fragColor = texture(u_tex, v_uv); }"
        )
        vao = self._make_fullscreen_vao(prog)
        tex.use(0)
        if 'u_tex' in prog: prog['u_tex'].value = 0

        vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(PASSES): vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        # Force actual GPU completion
        try: fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        bandwidth_gbps = (SIZE * 2 * PASSES) / (time.perf_counter() - start) / 1e9
        self._main_fbo.use()
        fbo.release(); tex.release()
        
        return {
            "name": "VRAM Bandwidth (4K Framebuffer Blit)",
            "value": round(bandwidth_gbps, 3), "unit": "GB/s",
            "raw": PASSES, "score": self._normalize(bandwidth_gbps, 0, 5000)
        }

    def test_particle_simulation(self) -> dict:
        self.progress_cb("GPU: Particle Physics Simulation...", 30)
        N_PARTICLES = 200_000
        vert_particle = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_uv;
        uniform float u_dt;
        uniform vec2  u_gravity;
        out vec2 v_uv;
        void main() {
            vec2 vel = in_uv + u_gravity * u_dt;
            vec2 pos_new = in_position + vel * u_dt;
            if (abs(pos_new.x) > 1.0) vel.x = -vel.x;
            if (abs(pos_new.y) > 1.0) vel.y = -vel.y;
            v_uv = vel;
            gl_Position = vec4(pos_new, 0.0, 1.0);
            gl_PointSize = 1.0;
        }
        """
        frag_particle = "#version 330 core\nin vec2 v_uv;\nout vec4 fragColor;\nvoid main() { fragColor = vec4(abs(v_uv), 0.5, 0.8); }"

        rng = np.random.default_rng(seed=42)
        positions = (rng.random((N_PARTICLES, 2), dtype=np.float32) * 2 - 1)
        velocities = (rng.random((N_PARTICLES, 2), dtype=np.float32) * 0.02 - 0.01)
        particle_data = np.column_stack([positions, velocities]).astype(np.float32)

        prog = self.ctx.program(vertex_shader=vert_particle, fragment_shader=frag_particle)
        vbo = self.ctx.buffer(particle_data.tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_position', 'in_uv')

        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        if 'u_dt' in prog: prog['u_dt'].value = 0.016
        if 'u_gravity' in prog: prog['u_gravity'].value = (0.0, -0.001)

        FRAMES = 200
        start = time.perf_counter()
        for _ in range(FRAMES):
            self.ctx.clear(0.02, 0.02, 0.05)
            vao.render(moderngl.POINTS)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = FRAMES / (time.perf_counter() - start)
        particles_per_sec = N_PARTICLES * fps
        return {
            "name": f"Particle Simulation ({N_PARTICLES:,} particles)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": FRAMES, "score": self._normalize(particles_per_sec / 1e9, 0, 50)
        }

    # ── EXTENDED TESTS ────────────────────────────────────────

    def test_ray_marching(self) -> dict:
        self.progress_cb("GPU: Ray Marching / Sphere Tracing...", 35)
        prog = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_RAY_MARCH)
        vao = self._quad_vao(prog)
        uniforms = {'u_time': 0.0, 'u_resolution': (float(self.WIDTH), float(self.HEIGHT))}
        
        n_frames = min(self.FRAMES, 100)
        self._set_uniforms(prog, uniforms)
        for _ in range(3): vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for i in range(n_frames):
            try: prog['u_time'].value = i * 0.016
            except Exception: pass
            vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = n_frames / (time.perf_counter() - start)
        gflops = (self.WIDTH * self.HEIGHT * 128 * 50 * fps) / 1e9
        return {
            "name": "Ray Marching — Animated SDF Scene",
            "value": round(fps, 2), "unit": "FPS",
            "gflops_est": round(gflops, 3), "raw": n_frames, "score": self._normalize(fps, 0, 2000)
        }

    def test_depth_of_field(self) -> dict:
        self.progress_cb("GPU: Depth of Field — Bokeh Blur...", 42)
        rng = np.random.default_rng(seed=42)
        y_coords = np.linspace(0, 1, self.HEIGHT, dtype=np.float32)
        x_coords = np.linspace(0, 1, self.WIDTH,  dtype=np.float32)
        xx, yy = np.meshgrid(x_coords, y_coords)
        r = (np.sin(xx * 6.28 * 4) * 0.5 + 0.5).astype(np.float32)
        g = (np.cos(yy * 6.28 * 3) * 0.5 + 0.5).astype(np.float32)
        b = (np.sin((xx + yy) * 6.28 * 2) * 0.5 + 0.5).astype(np.float32)
        a = np.ones_like(r)
        tex_data = np.stack([r, g, b, a], axis=-1)
        tex_data = (tex_data * 255).clip(0, 255).astype(np.uint8)

        scene_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, tex_data.tobytes())
        scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        scene_tex.use(0)

        prog = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_DOF)
        vao = self._quad_vao(prog)
        self._set_uniforms(prog, {'u_scene': 0, 'u_focal_dist': 0.5, 'u_aperture': 8.0, 'u_resolution': (float(self.WIDTH), float(self.HEIGHT))})

        elapsed = self._run_loop(vao, self.FRAMES)
        fps = self.FRAMES / elapsed
        gtex_s = 64 * self.WIDTH * self.HEIGHT * fps / 1e9
        scene_tex.release()
        
        return {
            "name": "Depth of Field — 64-Sample Bokeh Blur",
            "value": round(fps, 2), "unit": "FPS",
            "gtexels_sec": round(gtex_s, 3), "raw": self.FRAMES, "score": self._normalize(fps, 0, 3000)
        }

    def test_shadow_mapping(self) -> dict:
        self.progress_cb("GPU: Shadow Map Rendering (PCF 5×5)...", 49)
        SHADOW_RES = 2048
        shadow_depth = self.ctx.depth_texture((SHADOW_RES, SHADOW_RES))
        shadow_fbo = self.ctx.framebuffer(depth_attachment=shadow_depth)

        prog_depth = self.ctx.program(
            vertex_shader="#version 330 core\nin vec3 in_position;\nuniform mat4 u_light_mvp;\nvoid main() { gl_Position = u_light_mvp * vec4(in_position, 1.0); }",
            fragment_shader="#version 330 core\nvoid main() {}"
        )
        prog_light = self.ctx.program(vertex_shader=VERT_3D, fragment_shader=FRAG_SHADOW)

        verts, idxs = _gen_sphere_mesh(rings=64, sectors=64)
        vao_depth = self.ctx.vertex_array(prog_depth, [(self.ctx.buffer(verts.tobytes()), '3f 12x', 'in_position')], self.ctx.buffer(idxs.tobytes()))
        vao_light = self._mesh_vao(prog_light, verts, idxs)

        light_dir = np.array([1.0, 2.0, 1.5], dtype=np.float32)
        light_dir = light_dir / np.linalg.norm(light_dir)
        light_pos = light_dir * 10.0

        light_view = _look_at(light_pos, np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
        light_proj = _perspective(45.0, 1.0, 0.1, 50.0)
        light_vp = (light_proj @ light_view).astype(np.float32)

        cam_view = _look_at(np.array([0, 1, 4], dtype=np.float32), np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
        cam_proj = _perspective(60.0, self.WIDTH / self.HEIGHT, 0.1, 100.0)
        mvp = (cam_proj @ cam_view).astype(np.float32)

        if 'u_light_mvp' in prog_depth: prog_depth['u_light_mvp'].write(light_vp.tobytes())
        shadow_depth.use(0)
        self._set_uniforms(prog_light, {'u_shadow_map': 0, 'u_light_dir': tuple(light_dir), 'u_cam_pos': (0.0, 1.0, 4.0)})
        if 'u_light_vp' in prog_light: prog_light['u_light_vp'].write(light_vp.tobytes())
        if 'u_mvp' in prog_light: prog_light['u_mvp'].write(mvp.tobytes())
        if 'u_model' in prog_light: prog_light['u_model'].write(np.eye(4, dtype=np.float32).tobytes())
        if 'u_normal_mat' in prog_light: prog_light['u_normal_mat'].write(np.eye(3, dtype=np.float32).tobytes())

        for _ in range(3):
            shadow_fbo.use(); shadow_fbo.clear(); vao_depth.render(moderngl.TRIANGLES)
            self._main_fbo.use(); self._main_fbo.clear(); vao_light.render(moderngl.TRIANGLES)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(self.FRAMES):
            shadow_fbo.use(); shadow_fbo.clear(); vao_depth.render(moderngl.TRIANGLES)
            self._main_fbo.use(); self._main_fbo.clear(); vao_light.render(moderngl.TRIANGLES)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = self.FRAMES / (time.perf_counter() - start)
        shadow_fbo.release()
        return {
            "name": f"Shadow Map Rendering (PCF 5×5, {SHADOW_RES}² shadow map)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 4000)
        }

    def test_ssao(self) -> dict:
        self.progress_cb("GPU: Screen-Space Ambient Occlusion (SSAO)...", 56)
        pos_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, dtype='f4')
        nor_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, dtype='f4')
        dep_tex = self.ctx.depth_texture((self.WIDTH, self.HEIGHT))
        gbuf_fbo = self.ctx.framebuffer(color_attachments=[pos_tex, nor_tex], depth_attachment=dep_tex)

        prog_gbuf = self.ctx.program(vertex_shader=VERT_3D, fragment_shader=FRAG_GBUFFER)
        verts, idxs = _gen_sphere_mesh(rings=64, sectors=64)
        vao_gbuf = self._mesh_vao(prog_gbuf, verts, idxs)

        cam_view = _look_at(np.array([0, 1, 4], dtype=np.float32), np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
        cam_proj = _perspective(60.0, self.WIDTH / self.HEIGHT, 0.1, 100.0)
        mvp = (cam_proj @ cam_view).astype(np.float32)

        if 'u_mvp' in prog_gbuf: prog_gbuf['u_mvp'].write(mvp.tobytes())
        if 'u_model' in prog_gbuf: prog_gbuf['u_model'].write(np.eye(4, dtype=np.float32).tobytes())
        if 'u_normal_mat' in prog_gbuf: prog_gbuf['u_normal_mat'].write(np.eye(3, dtype=np.float32).tobytes())

        prog_ssao = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_SSAO)
        rng = np.random.default_rng(seed=0)
        samples = []
        for i in range(64):
            s = rng.standard_normal(3).astype(np.float32); s /= np.linalg.norm(s)
            s *= rng.uniform(0, 1)
            s *= 0.1 + 0.9 * ((i / 64.0) ** 2)
            samples.extend(s.tolist())

        noise_data = (rng.standard_normal((16, 3)).astype(np.float32) * 0.5 + 0.5)
        noise_data = (noise_data * 255).clip(0, 255).astype(np.uint8)
        noise_tex = self.ctx.texture((4, 4), 3, noise_data.tobytes())
        noise_tex.repeat_x = noise_tex.repeat_y = True

        pos_tex.use(0); nor_tex.use(1); noise_tex.use(2)
        vao_ssao = self._quad_vao(prog_ssao)

        self._set_uniforms(prog_ssao, {'u_position': 0, 'u_normal': 1, 'u_noise': 2, 'u_noise_scale': (self.WIDTH / 4.0, self.HEIGHT / 4.0)})
        if 'u_samples' in prog_ssao: prog_ssao['u_samples'].write(np.array(samples, dtype=np.float32).tobytes())
        if 'u_projection' in prog_ssao: prog_ssao['u_projection'].write(cam_proj.tobytes())

        for _ in range(3):
            gbuf_fbo.use(); gbuf_fbo.clear(); vao_gbuf.render(moderngl.TRIANGLES)
            self._main_fbo.use(); vao_ssao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(self.FRAMES):
            gbuf_fbo.use(); gbuf_fbo.clear(); vao_gbuf.render(moderngl.TRIANGLES)
            self._main_fbo.use(); self._main_fbo.clear(); vao_ssao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = self.FRAMES / (time.perf_counter() - start)
        gbuf_fbo.release(); noise_tex.release()

        return {
            "name": "Screen-Space Ambient Occlusion (SSAO, 64 samples)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 3500)
        }

    def test_gaussian_blur_multipass(self) -> dict:
        self.progress_cb("GPU: Multi-Pass Gaussian Blur...", 63)
        SIGMA, N_PASSES = 15.0, 6
        rng = np.random.default_rng(seed=99)
        tex_data = rng.integers(0, 256, (self.HEIGHT, self.WIDTH, 4), dtype=np.uint8)
        
        tex_a = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, tex_data.tobytes())
        tex_b = self.ctx.texture((self.WIDTH, self.HEIGHT), 4)
        fbo_a = self.ctx.framebuffer(color_attachments=[tex_a])
        fbo_b = self.ctx.framebuffer(color_attachments=[tex_b])

        prog_h = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_GAUSSIAN_H)
        prog_v = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_GAUSSIAN_V)

        self._set_uniforms(prog_h, {'u_tex': 0, 'u_resolution': (float(self.WIDTH), float(self.HEIGHT)), 'u_sigma': SIGMA})
        self._set_uniforms(prog_v, {'u_tex': 0, 'u_resolution': (float(self.WIDTH), float(self.HEIGHT)), 'u_sigma': SIGMA})

        vao_h = self._quad_vao(prog_h); vao_v = self._quad_vao(prog_v)

        for _ in range(3):
            tex_a.use(0); fbo_b.use(); vao_h.render(moderngl.TRIANGLE_STRIP)
            tex_b.use(0); fbo_a.use(); vao_v.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(self.FRAMES):
            for _p in range(N_PASSES // 2):
                tex_a.use(0); fbo_b.use(); vao_h.render(moderngl.TRIANGLE_STRIP)
                tex_b.use(0); fbo_a.use(); vao_v.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = self.FRAMES / (time.perf_counter() - start)
        fbo_a.release(); fbo_b.release()
        
        return {
            "name": f"Multi-Pass Gaussian Blur (σ={SIGMA:.0f}, {N_PASSES} passes)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 5000)
        }

    def test_parallax_mapping(self) -> dict:
        self.progress_cb("GPU: Normal + Parallax Occlusion Mapping...", 70)
        RES = 512
        rng = np.random.default_rng(seed=3)

        def gen_tex(data: np.ndarray) -> 'moderngl.Texture':
            d = (data * 255).clip(0, 255).astype(np.uint8)
            return self.ctx.texture((RES, RES), d.shape[-1], d.tobytes())

        y = np.linspace(0, 1, RES, dtype=np.float32); x = np.linspace(0, 1, RES, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        diffuse_data = np.stack([(0.8 + 0.2 * np.sin(xx * 32)).astype(np.float32), (0.4 + 0.1 * np.cos(yy * 16)).astype(np.float32), (0.2 * np.ones((RES, RES), dtype=np.float32)), np.ones((RES, RES), dtype=np.float32)], axis=-1)
        nx = (0.5 + 0.5 * np.sin(xx * 64 * 3.14)).astype(np.float32)
        ny = (0.5 + 0.5 * np.cos(yy * 64 * 3.14)).astype(np.float32)
        nz = np.ones((RES, RES), dtype=np.float32) * 0.9
        normal_data = np.stack([nx, ny, nz, np.ones((RES, RES), dtype=np.float32)], axis=-1)
        height_data = (0.5 + 0.5 * np.sin(xx * 16 * 3.14) * np.cos(yy * 16 * 3.14))[..., np.newaxis].astype(np.float32)

        diffuse_tex = gen_tex(diffuse_data); normal_tex = gen_tex(normal_data); height_tex = gen_tex(np.repeat(height_data, 3, axis=-1))
        diffuse_tex.use(0); normal_tex.use(1); height_tex.use(2)

        prog = self.ctx.program(vertex_shader=VERT_3D, fragment_shader=FRAG_PARALLAX)
        verts, idxs = _gen_sphere_mesh(rings=64, sectors=64)
        vao = self._mesh_vao(prog, verts, idxs)

        cam_view = _look_at(np.array([0, 1, 4], dtype=np.float32), np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
        cam_proj = _perspective(60.0, self.WIDTH / self.HEIGHT, 0.1, 100.0)
        mvp = (cam_proj @ cam_view).astype(np.float32)

        if 'u_mvp' in prog: prog['u_mvp'].write(mvp.tobytes())
        if 'u_model' in prog: prog['u_model'].write(np.eye(4, dtype=np.float32).tobytes())
        if 'u_normal_mat' in prog: prog['u_normal_mat'].write(np.eye(3, dtype=np.float32).tobytes())
        self._set_uniforms(prog, {'u_diffuse': 0, 'u_normal_map': 1, 'u_height_map': 2, 'u_light_pos': (3.0, 3.0, 3.0), 'u_view_pos': (0.0, 1.0, 4.0)})

        elapsed = self._run_loop(vao, self.FRAMES, mode=moderngl.TRIANGLES)
        fps = self.FRAMES / elapsed
        diffuse_tex.release(); normal_tex.release(); height_tex.release()

        return {
            "name": "Normal + Parallax Occlusion Mapping (32-step POM)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 4000)
        }

    def test_nbody_gravity(self) -> dict:
        self.progress_cb("GPU: GPU N-Body Gravity Simulation...", 77)
        N_BODIES = 1024
        rng = np.random.default_rng(seed=77)
        state = np.zeros((1, N_BODIES, 4), dtype=np.float32)
        angles = rng.uniform(0, 2 * math.pi, N_BODIES); radii = rng.uniform(0.1, 0.8, N_BODIES)
        state[0, :, 0] = (radii * np.cos(angles)).astype(np.float32); state[0, :, 1] = (radii * np.sin(angles)).astype(np.float32)
        state[0, :, 2] = (-radii * np.sin(angles) * 0.3).astype(np.float32); state[0, :, 3] = (radii * np.cos(angles) * 0.3).astype(np.float32)

        tex_a = self.ctx.texture((N_BODIES, 1), 4, state.tobytes(), dtype='f4')
        tex_b = self.ctx.texture((N_BODIES, 1), 4, dtype='f4')
        fbo_b = self.ctx.framebuffer(color_attachments=[tex_b])

        prog_update = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_NBODY)
        vao_update = self._quad_vao(prog_update)

        self._set_uniforms(prog_update, {'u_n_bodies': N_BODIES, 'u_dt': 0.016, 'u_softening': 0.01})

        prog_render = self.ctx.program(
            vertex_shader="#version 330 core\nuniform sampler2D u_state;\nuniform int u_n;\nvoid main() { int id = gl_VertexID; vec4 s = texelFetch(u_state, ivec2(id, 0), 0); gl_Position = vec4(s.xy, 0.0, 1.0); gl_PointSize = 2.0; }",
            fragment_shader="#version 330 core\nout vec4 fragColor;\nvoid main() { float d = length(gl_PointCoord - 0.5) * 2.0; if (d > 1.0) discard; fragColor = vec4(0.8, 0.6, 1.0, 1.0 - d); }"
        )
        vao_render = self.ctx.vertex_array(prog_render, [])
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE)

        n_frames = min(self.FRAMES, 150)

        tex_a.use(0); fbo_b.use()
        if 'u_positions' in prog_update: prog_update['u_positions'].value = 0
        vao_update.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(n_frames):
            tex_a.use(0); fbo_b.use()
            if 'u_positions' in prog_update: prog_update['u_positions'].value = 0
            vao_update.render(moderngl.TRIANGLE_STRIP)

            self._main_fbo.use(); self._main_fbo.clear(0.0, 0.0, 0.02, 1.0)
            tex_b.use(0)
            if 'u_state' in prog_render: prog_render['u_state'].value = 0
            if 'u_n' in prog_render: prog_render['u_n'].value = N_BODIES
            vao_render.render(moderngl.POINTS, vertices=N_BODIES)

        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        fps = n_frames / (time.perf_counter() - start)
        
        self.ctx.disable(moderngl.BLEND)
        fbo_b.release()
        return {
            "name": f"N-Body Gravity Simulation ({N_BODIES:,} bodies)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": n_frames, "score": self._normalize(fps, 0, 3000)
        }

    def test_perlin_terrain(self) -> dict:
        self.progress_cb("GPU: Perlin Noise Terrain Generation...", 84)
        prog = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_PERLIN)
        vao = self._quad_vao(prog)
        self._set_uniforms(prog, {'u_time': 0.0, 'u_octaves': 8, 'u_scale': 6.0})

        for _ in range(3): vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for i in range(self.FRAMES):
            try: prog['u_time'].value = i * 0.016
            except Exception: pass
            vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass
        
        fps = self.FRAMES / (time.perf_counter() - start)
        return {
            "name": "Perlin fBm Noise Terrain (8 Octaves)",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 4000)
        }

    def test_hdr_tonemapping(self) -> dict:
        self.progress_cb("GPU: ACES HDR Tone Mapping Pipeline...", 91)
        rng = np.random.default_rng(seed=11)
        hdr_data = rng.exponential(scale=2.0, size=(self.HEIGHT, self.WIDTH, 4)).astype(np.float32)
        hdr_data[..., 3] = 1.0

        hdr_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, hdr_data.tobytes(), dtype='f4')
        hdr_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        hdr_tex.use(0)

        prog = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_TONEMAPPING)
        vao = self._quad_vao(prog)
        self._set_uniforms(prog, {'u_hdr': 0, 'u_exposure': 1.0, 'u_passes': 3})

        elapsed = self._run_loop(vao, self.FRAMES)
        fps = self.FRAMES / elapsed
        hdr_tex.release()

        return {
            "name": "ACES HDR Tone Mapping Pipeline",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 6000)
        }

    def test_deferred_rendering(self) -> dict:
        self.progress_cb("GPU: Deferred Rendering — G-Buffer + 32 Lights...", 98)
        N_LIGHTS = 32
        pos_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, dtype='f4')
        nor_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, dtype='f4')
        alb_tex = self.ctx.texture((self.WIDTH, self.HEIGHT), 4, dtype='f4')
        dep_tex = self.ctx.depth_texture((self.WIDTH, self.HEIGHT))
        gbuf_fbo = self.ctx.framebuffer(color_attachments=[pos_tex, nor_tex, alb_tex], depth_attachment=dep_tex)

        prog_light = self.ctx.program(vertex_shader=VERT_FULLSCREEN, fragment_shader=FRAG_DEFERRED_LIGHTING)
        prog_gbuf = self.ctx.program(vertex_shader=VERT_3D, fragment_shader=FRAG_GBUFFER)

        verts, idxs = _gen_sphere_mesh(rings=128, sectors=128)
        vao_gbuf = self._mesh_vao(prog_gbuf, verts, idxs)
        vao_light = self._quad_vao(prog_light)

        cam_view = _look_at(np.array([0, 1, 4], dtype=np.float32), np.zeros(3, dtype=np.float32), np.array([0, 1, 0], dtype=np.float32))
        cam_proj = _perspective(60.0, self.WIDTH / self.HEIGHT, 0.1, 100.0)
        mvp = (cam_proj @ cam_view).astype(np.float32)

        if 'u_mvp' in prog_gbuf: prog_gbuf['u_mvp'].write(mvp.tobytes())
        if 'u_model' in prog_gbuf: prog_gbuf['u_model'].write(np.eye(4, dtype=np.float32).tobytes())
        if 'u_normal_mat' in prog_gbuf: prog_gbuf['u_normal_mat'].write(np.eye(3, dtype=np.float32).tobytes())

        rng = np.random.default_rng(seed=44)
        light_pos = (rng.uniform(-3, 3, (N_LIGHTS, 3))).astype(np.float32)
        light_col = (rng.uniform(0.2, 1.0, (N_LIGHTS, 3))).astype(np.float32)

        pos_tex.use(0); nor_tex.use(1); alb_tex.use(2)
        self._set_uniforms(prog_light, {'u_gPosition': 0, 'u_gNormal': 1, 'u_gAlbedoSpec': 2, 'u_view_pos': (0.0, 1.0, 4.0)})
        if 'u_lights' in prog_light: prog_light['u_lights'].write(light_pos.tobytes())
        if 'u_light_colors' in prog_light: prog_light['u_light_colors'].write(light_col.tobytes())

        for _ in range(3):
            gbuf_fbo.use(); gbuf_fbo.clear(); vao_gbuf.render(moderngl.TRIANGLES)
            self._main_fbo.use(); self._main_fbo.clear()
            pos_tex.use(0); nor_tex.use(1); alb_tex.use(2); vao_light.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        start = time.perf_counter()
        for _ in range(self.FRAMES):
            gbuf_fbo.use(); gbuf_fbo.clear(); vao_gbuf.render(moderngl.TRIANGLES)
            self._main_fbo.use(); self._main_fbo.clear()
            pos_tex.use(0); nor_tex.use(1); alb_tex.use(2); vao_light.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()
        try: self._main_fbo.read(viewport=(0, 0, 1, 1), components=4)
        except Exception: pass

        fps = self.FRAMES / (time.perf_counter() - start)
        gbuf_fbo.release()

        return {
            "name": f"Deferred Rendering G-Buffer + {N_LIGHTS} Point Lights",
            "value": round(fps, 2), "unit": "FPS",
            "raw": self.FRAMES, "score": self._normalize(fps, 0, 3000)
        }

    # ── RUN ALL ───────────────────────────────────────────────

    def run_all(self) -> dict:
        if not MODERNGL_AVAILABLE:
            return {
                "component": "GPU",
                "overall_score": 0, "grade": "N/A", "tier": "N/A",
                "error": "Run: pip install moderngl pygame",
                "tests": []
            }

        try:
            self._init_context()
        except Exception as e:
            return {"component": "GPU", "overall_score": 0, "error": str(e), "tests": []}

        gpu_info = {}
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    gpu_info = {"name": g.name, "vram_mb": g.memoryTotal, "driver": g.driver, "temperature": g.temperature}
            except Exception: pass

        tests = [
            # Basic Tests
            self.test_mandelbrot,
            self.test_lighting,
            self.test_texture_sampling,
            self.test_vertex_throughput,
            self.test_gpu_memory_bandwidth,
            self.test_particle_simulation,
            # Extended Tests
            self.test_ray_marching,
            self.test_depth_of_field,
            self.test_shadow_mapping,
            self.test_ssao,
            self.test_gaussian_blur_multipass,
            self.test_parallax_mapping,
            self.test_nbody_gravity,
            self.test_perlin_terrain,
            self.test_hdr_tonemapping,
            self.test_deferred_rendering,
        ]

        results = []
        for fn in tests:
            try: results.append(fn())
            except Exception as e: results.append({"name": fn.__name__, "error": str(e), "score": 0})

        if self.ctx:
            try: self.ctx.release()
            except Exception: pass

        scoreable = [r["score"] for r in results if "score" in r and "error" not in r]
        overall = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("GPU Benchmark Complete!", 100)

        return {
            "component": "GPU",
            "overall_score": overall, "grade": self._grade(overall), "tier": self._tier(overall),
            "gpu_info": gpu_info, "tests": results
        }

    @staticmethod
    def _normalize(value, low, high, out_min=0, out_max=100_000):
        if high == low: return out_min
        return int(out_min + (max(low, min(high, value)) - low) / (high - low) * (out_max - out_min))

    @staticmethod
    def _grade(score):
        if score >= 85_000: return "S"
        if score >= 70_000: return "A"
        if score >= 55_000: return "B"
        if score >= 40_000: return "C"
        if score >= 25_000: return "D"
        return "F"

    @staticmethod
    def _tier(score):
        if score >= 85_000: return "RTX 4080/4090 · RX 7900 XTX"
        if score >= 70_000: return "RTX 3080/4070 · RX 6900 XT"
        if score >= 55_000: return "RTX 3070 · RX 6800"
        if score >= 40_000: return "RTX 3060 · RX 6700 XT"
        if score >= 25_000: return "GTX 1660 Ti · RX 5600 XT"
        return "Integrated / Legacy GPU"
