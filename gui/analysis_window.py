"""
Analysis Window - Displays AI Diagnostic Results
"""

import customtkinter as ctk
import config
import json
from typing import Dict, Any

class AnalysisWindow(ctk.CTkToplevel):
    def __init__(self, parent, analysis_data: Dict[str, Any]):
        super().__init__(master=parent)
        
        self.analysis_data = analysis_data
        self.title("AI System Diagnostics")
        self.geometry("1000x800")
        
        # Make modal-like
        self.transient(parent)
        self.lift()
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create modern analysis widgets"""
        self.configure(fg_color="#0a0a0a")
        
        # Main scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 1. Header Area
        self.create_header_section()
        
        # 2. Main content cards
        if 'component_ratings' in self.analysis_data.get('data', {}):
            self.create_ratings_section()
        
        if 'components' in self.analysis_data.get('data', {}):
            self.create_benchmark_section()
        
        # 3. Detailed Analysis
        self.create_details_section()
        
        # Footer Action
        ctk.CTkButton(
            self,
            text="Close Report",
            command=self.destroy,
            height=45,
            width=200,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=config.ACCENT_COLOR
        ).pack(pady=20)

    def create_header_section(self):
        """Create premium header with summary"""
        header_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 25))
        
        title_badge = ctk.CTkLabel(header_frame, text=" AMAZON NOVA AI INSIGHT ", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#6c5ce7", text_color="white", corner_radius=5)
        title_badge.pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            header_frame,
            text="System Intelligence Report",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white"
        ).pack(anchor="w")
        
        # Summary card
        summary_card = ctk.CTkFrame(header_frame, fg_color=config.get_card_bg(), corner_radius=15, border_width=1, border_color="#333333")
        summary_card.pack(fill="x", pady=(20, 0))
        
        summary_text = self.analysis_data.get('data', {}).get('summary', 'Detailed analysis report from Nova AI.')
        if not self.analysis_data.get('is_json'):
            summary_text = "Analysis complete. Review the findings below."
            
        ctk.CTkLabel(
            summary_card,
            text=summary_text,
            font=ctk.CTkFont(size=15),
            wraplength=900,
            justify="left",
            padx=25,
            pady=25
        ).pack(fill="x")

    def create_ratings_section(self):
        """Create component ratings grid with card style"""
        analysis_type = self.analysis_data.get('analysis_type')
        if analysis_type in ['logs', 'sensor']:
            return

        if not self.analysis_data.get('is_json'):
            return

        ratings = self.analysis_data.get('data', {}).get('component_ratings', {})
        if not ratings:
            return
            
        # If all ratings are unknown, don't show the section (common in logs/csv analysis)
        if all(val.lower() == 'unknown' for val in ratings.values()):
            return
        
        # Grid container
        grid_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 25))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        components = [('cpu', '💻 CPU'), ('gpu', '🎮 GPU'), ('ram', '🧠 RAM'), ('storage', '💽 Disk')]
        for i, (key, label) in enumerate(components):
            rating = ratings.get(key, 'Unknown')
            color = self._get_rating_color(rating)
            
            card = ctk.CTkFrame(grid_frame, fg_color=config.get_card_bg(), corner_radius=15, border_width=1, border_color="#2b2b2b")
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(pady=(15, 5))
            ctk.CTkLabel(card, text=rating.upper(), font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack(pady=(0, 15))

    def create_benchmark_section(self):
        """Create specialized benchmark comparison section"""
        analysis_type = self.analysis_data.get('analysis_type')
        if analysis_type in ['logs', 'sensor']:
            return
            
        data = self.analysis_data.get('data', {})
        components = data.get('components', {})
        
        if not components or all(not info.get('model') or info.get('model') == 'Unknown' for info in components.values()):
            return
            
        title_label = ctk.CTkLabel(self.scroll_frame, text="HISTORICAL PERFORMANCE ANALYSIS", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        title_label.pack(anchor="w", padx=5, pady=(10, 10))
        
        for key, info in components.items():
            card = ctk.CTkFrame(self.scroll_frame, fg_color=config.get_card_bg(), corner_radius=15, border_width=1, border_color="#333333")
            card.pack(fill="x", pady=5)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=25, pady=20)
            
            # Left side: Icon and Names
            left_info = ctk.CTkFrame(content, fg_color="transparent")
            left_info.pack(side="left", fill="both", expand=True)
            
            ctk.CTkLabel(left_info, text=key.upper(), font=ctk.CTkFont(size=11, weight="bold"), text_color=config.ACCENT_COLOR, anchor="w").pack(fill="x")
            ctk.CTkLabel(left_info, text=info.get('model', 'Unknown'), font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(left_info, text=info.get('explanation', ''), font=ctk.CTkFont(size=13), text_color="gray", anchor="w", justify="left", wraplength=500).pack(fill="x", pady=(5, 0))

            # Right side: Stats
            stats_side = ctk.CTkFrame(content, fg_color="transparent", width=250)
            stats_side.pack(side="right", fill="y", padx=(20, 0))
            
            self._create_stat_line(stats_side, "Original Score", info.get('original_release_score', 'N/A'), "gray")
            self._create_stat_line(stats_side, "Current Score", info.get('current_score', 'N/A'), "white")
            
            reduction = info.get('performance_reduction', '0%')
            self._create_stat_line(stats_side, "Efficiency Loss", reduction, "#e74c3c")

    def _create_stat_line(self, parent, label, value, color):
        line = ctk.CTkFrame(parent, fg_color="transparent")
        line.pack(fill="x", pady=2)
        ctk.CTkLabel(line, text=label, font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")
        ctk.CTkLabel(line, text=value, font=ctk.CTkFont(size=13, weight="bold"), text_color=color).pack(side="right")

    def create_details_section(self):
        """Create detailed analysis sections with cards"""
        details = self.analysis_data.get('data', {}).get('detailed_analysis', {})
        
        if not self.analysis_data.get('is_json'):
            raw_text = self.analysis_data.get('recommendations', 'No data available.')
            self._create_detailed_card("Full Analysis Breakdown", [raw_text])
            return

        if 'assessment' in details:
            self._create_detailed_card("Expert Assessment", [details['assessment']])

        if 'bottlenecks' in details:
            self._create_detailed_card("⚠️ Detected Bottlenecks", details['bottlenecks'], is_list=True)
            
        if 'optimization_tips' in details:
            self._create_detailed_card("🚀 System Optimizations", details['optimization_tips'], is_list=True)
            
        if 'upgrade_recommendations' in details:
            self._create_detailed_card("🔧 Recommended Upgrades", details['upgrade_recommendations'], is_list=True)

    def _create_detailed_card(self, title, items, is_list=False):
        if not items: return
        
        card = ctk.CTkFrame(self.scroll_frame, fg_color=config.get_card_bg(), corner_radius=15, border_width=1, border_color="#2b2b2b")
        card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(card, text=title.upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w", padx=25, pady=(20, 5))
        
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=25, pady=(0, 25))
        
        if is_list:
            for item in items:
                ctk.CTkLabel(content_frame, text=f"• {item}", font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=850).pack(fill="x", pady=2)
        else:
            ctk.CTkLabel(content_frame, text=items[0], font=ctk.CTkFont(size=14), anchor="w", justify="left", wraplength=850).pack(fill="x")

    def _get_rating_color(self, rating):
        rating = rating.lower()
        if any(x in rating for x in ["excellent", "good", "perfect"]): return "#2ecc71"
        if "fair" in rating: return "#f1c40f"
        if any(x in rating for x in ["poor", "bad", "critical"]): return "#e74c3c"
        return "gray"
