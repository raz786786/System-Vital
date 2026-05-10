"""
Google Gemini AI Analyzer Module
Provides intelligent hardware analysis and recommendations using Google Gemini API.
Uses the modern google.genai SDK (v1.x).
"""

import json
import re
from typing import Dict, Optional, List
from utils.logger import setup_logger
import config

logger = setup_logger(__name__)

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai SDK not installed. Run: pip install google-genai")


class GeminiAnalyzer:
    """AI-powered hardware analysis using Google Gemini"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL_NAME
        self._client = None
        self._ready = False
        
        self._ensure_client()
    
    def _ensure_client(self):
        """Create or recreate the genai Client when the key changes."""
        key = (self.api_key or "").strip()
        if not key or not GENAI_AVAILABLE:
            self._ready = False
            if not GENAI_AVAILABLE:
                logger.warning("google-genai SDK not installed")
            else:
                logger.warning("Google Gemini API key not configured")
            return
        
        try:
            self._client = genai.Client(api_key=key)
            self._ready = True
            logger.info(f"Google Gemini AI initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Gemini: {e}")
            self._ready = False
    
    def _generate(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response"""
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text.strip()
    
    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from a Gemini response, handling markdown fences"""
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        return json.loads(text.strip())
    
    def analyze_system(self, hardware_info: Dict, benchmark_results: Dict = None,
                      diagnostic_results: Dict = None) -> Dict:
        """Analyze complete system and provide recommendations"""
        if not self._ready:
            return {
                'available': False,
                'message': 'Google Gemini AI not configured. Add API key in settings.'
            }
        
        logger.info("Analyzing system with Google Gemini AI...")
        
        try:
            prompt = self._build_analysis_prompt(hardware_info, benchmark_results, diagnostic_results)
            text = self._generate(prompt)
            
            try:
                analysis_data = self._parse_json_response(text)
                analysis = {
                    'available': True,
                    'data': analysis_data,
                    'is_json': True,
                    'timestamp': None,
                }
            except json.JSONDecodeError:
                analysis = {
                    'available': True,
                    'recommendations': text,
                    'is_json': False,
                    'timestamp': None,
                }
            
            logger.info("AI analysis completed")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return {
                'available': False,
                'error': str(e),
                'message': 'Failed to get AI recommendations'
            }
    
    def get_upgrade_recommendations(self, hardware_info: Dict, budget: str = "moderate") -> Dict:
        """Get upgrade recommendations based on current hardware"""
        if not self._ready:
            return {'available': False}
        
        logger.info(f"Getting upgrade recommendations (budget: {budget})...")
        
        try:
            prompt = f"""
            Analyze this PC hardware and suggest upgrades for a {budget} budget:
            
            CPU: {hardware_info.get('cpu', {}).get('name', 'Unknown')}
            GPU: {hardware_info.get('gpu', [{}])[0].get('name', 'Unknown') if hardware_info.get('gpu') else 'Unknown'}
            RAM: {hardware_info.get('ram', {}).get('total_formatted', 'Unknown')}
            
            Provide:
            1. Which component to upgrade first and why
            2. Specific product recommendations
            3. Expected performance improvement
            4. Estimated cost
            
            Keep recommendations practical and specific.
            """
            
            text = self._generate(prompt)
            return {
                'available': True,
                'recommendations': text,
                'budget': budget
            }
            
        except Exception as e:
            logger.error(f"Error getting upgrade recommendations: {e}")
            return {'available': False, 'error': str(e)}
    
    def diagnose_performance_issues(self, hardware_info: Dict, symptoms: str) -> Dict:
        """Diagnose performance issues based on symptoms"""
        if not self._ready:
            return {'available': False}
        
        logger.info("Diagnosing performance issues...")
        
        try:
            prompt = f"""
            User reports these performance issues: {symptoms}
            
            Their hardware:
            CPU: {hardware_info.get('cpu', {}).get('name', 'Unknown')}
            GPU: {hardware_info.get('gpu', [{}])[0].get('name', 'Unknown') if hardware_info.get('gpu') else 'Unknown'}
            RAM: {hardware_info.get('ram', {}).get('total_formatted', 'Unknown')}
            
            Provide:
            1. Most likely causes
            2. Step-by-step troubleshooting
            3. Potential solutions
            
            Be specific and actionable.
            """
            
            text = self._generate(prompt)
            return {
                'available': True,
                'diagnosis': text
            }
            
        except Exception as e:
            logger.error(f"Error diagnosing issues: {e}")
            return {'available': False, 'error': str(e)}
    
    def _build_analysis_prompt(self, hardware_info: Dict, benchmark_results: Dict = None,
                                diagnostic_results: Dict = None) -> str:
        """Build comprehensive analysis prompt"""
        
        cpu_info = hardware_info.get('cpu', {})
        gpu_info = hardware_info.get('gpu', [{}])[0] if hardware_info.get('gpu') else {}
        ram_info = hardware_info.get('ram', {})
        
        prompt = f"""
        Analyze this PC configuration and provide expert recommendations:
        
        HARDWARE:
        - CPU: {cpu_info.get('name', 'Unknown')} ({cpu_info.get('cores', '?')} cores, {cpu_info.get('threads', '?')} threads)
        - GPU: {gpu_info.get('name', 'Unknown')} ({gpu_info.get('vram_formatted', 'Unknown VRAM')})
        - RAM: {ram_info.get('total_formatted', 'Unknown')} ({len(ram_info.get('modules', []))} modules)
        - Storage: {len(hardware_info.get('storage', []))} drive(s)
        """
        
        if benchmark_results:
            prompt += f"\n\nBENCHMARK RESULTS:\n{json.dumps(benchmark_results, indent=2)}"
        
        if diagnostic_results and diagnostic_results.get('issues'):
            issues_summary = f"{diagnostic_results.get('summary', {}).get('critical', 0)} critical, "
            issues_summary += f"{diagnostic_results.get('summary', {}).get('warnings', 0)} warnings"
            prompt += f"\n\nDETECTED ISSUES: {issues_summary}"
        
        prompt += """
        
        Provide the output strictly in valid JSON format with the following structure:
        {
            "summary": "Overall system assessment summary (max 2 sentences)",
            "component_ratings": {
                "cpu": "Rating (e.g., Poor, Fair, Good, Excellent)",
                "gpu": "Rating",
                "ram": "Rating",
                "storage": "Rating"
            },
            "detailed_analysis": {
                "assessment": "Detailed assessment...",
                "bottlenecks": ["Bottleneck 1", "Bottleneck 2"],
                "optimization_tips": ["Tip 1", "Tip 2"],
                "upgrade_recommendations": ["Rec 1", "Rec 2"]
            }
        }
        """
        
        return prompt
    
    def analyze_userbenchmark_text(self, hardware_info: Dict, raw_text: str) -> Dict:
        """Analyze raw UserBenchmark result text using Gemini"""
        if not self._ready:
            return {'available': False, 'message': 'Gemini not initialized'}

        logger.info("Analyzing UserBenchmark text with Gemini...")
        
        cpu_name = hardware_info.get('cpu', {}).get('name', 'Unknown CPU')
        gpu_name = hardware_info.get('gpu', [{}])[0].get('name', 'Unknown GPU')
        
        prompt = f"""
        I have pasted the raw text results from a UserBenchmark run below. 
        My detected hardware:
        - CPU: {cpu_name}
        - GPU: {gpu_name}
        
        --- USERBENCHMARK TEXT START ---
        {raw_text}
        --- USERBENCHMARK TEXT END ---
        
        Task:
        1. Extract the current Percentile/Score for the CPU, GPU, and SSD from the pasted text.
        2. EXTREMELY IMPORTANT: Search your knowledge for the standard/average benchmark scores for these specific components (e.g., {cpu_name}) WHEN THEY WERE ORIGINALLY RELEASED. 
           - Look for initial review data or launch benchmarks.
        3. Compare the CURRENT MEASURED performance to that ORIGINAL RELEASE performance.
        4. Calculate "Performance Reduction %" (how much it has slowed down since it was new).
        5. Provide a clear "Health Report" based on this degradation.
        
        Provide the output strictly in valid JSON format with this structure:
        {{
            "summary": "Overall system health summary focusing on performance loss over time",
            "components": {{
                "cpu": {{
                    "model": "{cpu_name}",
                    "current_score": "XX%", 
                    "original_release_score": "YY%",
                    "performance_reduction": "Z%",
                    "status": "Healthy/Degraded/Critical",
                    "explanation": "Brief context on why performance might have dropped (e.g., dust, thermal paste, software overhead)"
                }},
                "gpu": {{ ... }},
                "drive": {{ ... }}
            }}
        }}
        
        Do not include markdown code blocks. Just the raw JSON.
        """
        
        try:
            text = self._generate(prompt)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
                
            data = json.loads(json_str)
            return {'available': True, 'data': data, 'analysis_type': 'benchmark'}
            
        except Exception as e:
            logger.error(f"Error analyzing UserBenchmark text: {e}")
            return {'available': False, 'message': str(e)}

    def analyze_sensor_log(self, hardware_info: Dict, csv_path: str) -> Dict:
        """Analyze HWiNFO CSV log using Gemini"""
        if not self._ready:
            return {'available': False, 'message': 'Gemini not initialized'}

        logger.info(f"Analyzing sensor log: {csv_path}")
        
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.splitlines()
            if len(lines) < 2:
                return {'available': False, 'message': 'Log file is empty or invalid'}
                
            header = lines[0]
            sample_count = 20
            step = max(1, len(lines) // sample_count)
            
            sampled_rows = []
            for i in range(1, len(lines), step):
                sampled_rows.append(lines[i])
                if len(sampled_rows) >= sample_count:
                    break
            
            csv_sample = header + "\n" + "\n".join(sampled_rows)
            cpu_name = hardware_info.get('cpu', {}).get('name', 'Unknown CPU')
            
            prompt = f"""
            I have a CSV sensor log from HWiNFO64 below. This represents a system under {cpu_name}.
            
            TASK: 
            1. Analyze the temperatures, clock speeds, and voltages in this CSV sample.
            2. Identify any anomalies (thermal throttling, voltage dips, unusual fan speeds, or high background load).
            3. Based on these sensors, provide a "Famous Troubleshooting" diagnosis (e.g., 'Your CPU is thermal throttling because it hits 100C').
            
            --- HWINFO CSV SAMPLE START ---
            {csv_sample}
            --- HWINFO CSV SAMPLE END ---
            
            Provide the output strictly in valid JSON format with this structure:
            {{
                "summary": "Overall sensor health summary",
                "is_json": true,
                "data": {{
                    "component_ratings": {{
                        "cpu": "Excellent/Fair/Poor",
                        "gpu": "...",
                        "ram": "...",
                        "storage": "..."
                    }},
                    "detailed_analysis": {{
                        "assessment": "Detailed assessment of sensors...",
                        "bottlenecks": ["List of sensor-based issues found"],
                        "optimization_tips": ["Steps to fix these hardware issues"],
                        "upgrade_recommendations": ["Hardware upgrades if failing"]
                    }}
                }}
            }}
            """
            
            text = self._generate(prompt)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
                
            data = json.loads(json_str)
            return {'available': True, 'data': data.get('data', {}), 'is_json': True, 'analysis_type': 'sensor'}
        except Exception as e:
            logger.error(f"Error analyzing sensor log: {e}")
            return {'available': False, 'message': str(e)}

    def analyze_novabench_text(self, hardware_info: Dict, raw_text: str) -> Dict:
        """Analyze Novabench raw results using Gemini"""
        if not self._ready:
            return {'available': False, 'message': 'Gemini not initialized'}

        logger.info("Analyzing Novabench text via Gemini...")
        
        try:
            clean_text = "\n".join([line.strip() for line in raw_text.splitlines() if line.strip()])
            
            prompt = f"""
            You are a hardware expert. I have Novabench benchmark results for a system.
            System detected: {json.dumps(hardware_info)}
            
            NOVABENCH RAW TEXT:
            ---
            {clean_text}
            ---
            
            TASK:
            1. Extract the Novabench scores (Total Score, CPU Score, GPU Score, RAM Score, Disk/Storage Score).
            2. Research or estimate the "Original Release" scores for exactly this {hardware_info.get('cpu', {}).get('name', 'hardware')} and GPU.
            3. Calculate "Performance Reduction %" = (1 - Current Score / Original Release Score) * 100.
            4. Provide a status (EXCELLENT, FAIR, POOR, CRITICAL) for each component.
            5. Provide a summary assessment and optimization tips.
            
            Return ONLY a valid JSON object:
            {{
                "summary": "Overall system health summary...",
                "data": {{
                    "components": {{
                        "cpu": {{
                            "model": "exact model name",
                            "current_score": 1234,
                            "original_release_score": 1500,
                            "performance_reduction": "17.7%",
                            "status": "FAIR",
                            "explanation": "Brief explanation..."
                        }},
                        "gpu": {{ ... }},
                        "ram": {{ ... }},
                        "drive": {{ ... }}
                    }},
                    "detailed_analysis": {{
                        "assessment": "...",
                        "bottlenecks": ["..."],
                        "optimization_tips": ["..."],
                        "upgrade_recommendations": ["..."]
                    }},
                    "component_ratings": {{
                        "cpu": "Fair",
                        "gpu": "...",
                        "ram": "...",
                        "storage": "..."
                    }}
                }}
            }}
            """
            
            text = self._generate(prompt)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
                
            data = json.loads(json_str)
            return {'available': True, 'data': data.get('data', {}), 'analysis_type': 'benchmark'}

        except Exception as e:
            logger.error(f"Error analyzing Novabench text: {e}")
            return {'available': False, 'message': str(e)}

    def analyze_event_logs(self, hardware_info: Dict, logs: Dict[str, List[Dict]]) -> Dict:
        """Analyze Windows Event Logs using Gemini"""
        if not self._ready:
            return {'available': False, 'message': 'Gemini not initialized'}

        logger.info("Analyzing Windows Event Logs via Gemini...")
        
        try:
            system_summary = ""
            for err in logs.get('system', [])[:15]:
                system_summary += f"- [{err['time']}] {err['source']} (ID: {err['event_id']}): {err['message'][:200]}\n"
                
            app_summary = ""
            for err in logs.get('application', [])[:15]:
                app_summary += f"- [{err['time']}] {err['source']} (ID: {err['event_id']}): {err['message'][:200]}\n"

            prompt = f"""
            You are a Windows System Internal expert. Analyze these recent Critical/Error event logs for this PC:
            
            HARDWARE:
            - CPU: {hardware_info.get('cpu', {}).get('name', 'Unknown')}
            - GPU: {hardware_info.get('gpu', [{}])[0].get('name', 'Unknown') if hardware_info.get('gpu') else 'Unknown'}
            
            SYSTEM EVENT LOG ERRORS:
            {system_summary if system_summary else "No system errors found."}
            
            APPLICATION EVENT LOG ERRORS:
            {app_summary if app_summary else "No application errors found."}
            
            TASK:
            1. Identify if any of these logs indicate HARDWARE FAILURE (e.g., WHEA errors, Disk bad sectors, Power-Kernel issues).
            2. Identify major SOFTWARE INSTABILITY (e.g., driver crashes, critical service failures).
            3. Provide a clear diagnosis: Is the hardware failing, or is it a software/driver issue?
            
            Return ONLY a valid JSON object:
            {{
                "summary": "Overall system stability assessment...",
                "is_json": true,
                "data": {{
                    "component_ratings": {{
                        "system_stability": "Healthy/Unstable/Critical",
                        "hardware_health": "Healthy/Suspect/Failing"
                    }},
                    "detailed_analysis": {{
                        "assessment": "Detailed breakdown of the most critical log findings...",
                        "bottlenecks": ["List of specific root causes found in logs"],
                        "optimization_tips": ["Actionable steps to resolve these specific errors"],
                        "upgrade_recommendations": ["Hardware replacements if failures are detected"]
                    }}
                }}
            }}
            """
            
            text = self._generate(prompt)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
                
            data = json.loads(json_str)
            return {'available': True, 'data': data.get('data', {}), 'is_json': True, 'analysis_type': 'logs'}

        except Exception as e:
            logger.error(f"Error analyzing event logs: {e}")
            return {'available': False, 'message': str(e)}

    def compare_benchmarks(self, hardware_info: Dict, benchmark_results: Dict) -> Dict:
        """Compare actual benchmark scores against historical release data using Gemini"""
        if not self._ready:
            return {'available': False, 'message': 'Gemini not initialized'}

        logger.info("Comparing benchmarks with Gemini...")
        
        cpu_name = hardware_info.get('cpu', {}).get('name', 'Unknown CPU')
        gpu_name = hardware_info.get('gpu', [{}])[0].get('name', 'Unknown GPU')
        
        single_core = benchmark_results.get('single_core', 'N/A')
        multi_core = benchmark_results.get('multi_core', 'N/A')
        
        prompt = f"""
        I have run a Geekbench 6 benchmark on a computer with the following components:
        
        CPU: {cpu_name}
        GPU: {gpu_name}
        
        Actual Measured Scores:
        - Single-Core Score: {single_core}
        - Multi-Core Score: {multi_core}
        
        Task:
        1. Identify the standard/average Geekbench 6 scores for these specific components when they were originally released (search your knowledge base).
        2. Compare my actual scores to these original averages.
        3. Calculate a "health percentage" (Actual / Expected * 100).
        4. Rate the performance status (e.g., "Performing as expected", "Underperforming", "Thermal Throttling likely").
        
        Provide the output strictly in valid JSON format with this structure:
        {{
            "cpu": {{
                "model": "{cpu_name}",
                "measured_single": {single_core},
                "expected_single": 0,
                "measured_multi": {multi_core},
                "expected_multi": 0,
                "health_percentage": 0,
                "status": "String evaluation",
                "explanation": "Brief explanation of result"
            }},
            "summary": "Overall system health summary based on scores"
        }}
        
        Do not include markdown code blocks. Just the raw JSON.
        """
        
        try:
            text = self._generate(prompt)
            if text.startswith('```json'): text = text[7:]
            if text.endswith('```'): text = text[:-3]
            
            data = json.loads(text.strip())
            return {'available': True, 'data': data, 'analysis_type': 'benchmark'}
            
        except Exception as e:
            logger.error(f"Error comparing benchmarks: {e}")
            return {'available': False, 'message': str(e)}
