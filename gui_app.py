#!/usr/bin/env python3
"""
GUI Application for ASIC Verification Automation
Provides a user-friendly interface for all automation features
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import sys
import os
from pathlib import Path
import subprocess
import json
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT_DIR))

from scripts import common_utils
from scripts.automator import ASICVerificationAutomator

class ASICVerificationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("genToast: ASIC Verification agent Suite")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Configure styles
        self.setup_styles()
        
        # Initialize variables
        self.api_key = tk.StringVar(value=os.getenv('OPENROUTER_API_KEY', ''))
        self.model_name = tk.StringVar(value=os.getenv('DEEPSEEK_MODEL_NAME_DEFAULT', 'deepseek/deepseek-chat-v3-0324:free'))
        self.output_queue = queue.Queue()
        self.automator = None
        
        # Create main interface
        self.create_widgets()
        
        # Start output monitoring
        self.monitor_output()
        
    def setup_styles(self):
        """Configure ttk styles for a professional look"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Error.TLabel', foreground='red', font=('Arial', 10, 'bold'))
        style.configure('Action.TButton', padding=(10, 5))
        
    def create_widgets(self):
        """Create the main GUI interface"""
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_setup_tab()
        self.create_plan_generation_tab()
        self.create_test_generation_tab()
        self.create_uvm_tab()
        self.create_utilities_tab()
        self.create_console_tab()
        
    def create_setup_tab(self):
        """Create setup and configuration tab"""
        setup_frame = ttk.Frame(self.notebook)
        self.notebook.add(setup_frame, text="Setup & Config")
        
        # Main container with padding
        main_container = ttk.Frame(setup_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="ASIC Verification Automation Setup", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # API Configuration Section
        api_frame = ttk.LabelFrame(main_container, text="API Configuration", padding=15)
        api_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(api_frame, text="OpenRouter API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=60, show="*")
        api_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Label(api_frame, text="Model Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        model_entry = ttk.Entry(api_frame, textvariable=self.model_name, width=60)
        model_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=5)
        
        # Test API button
        test_api_btn = ttk.Button(api_frame, text="Test API Connection", command=self.test_api_connection)
        test_api_btn.grid(row=2, column=0, pady=10, sticky=tk.W)
        
        # Status label
        self.api_status_label = ttk.Label(api_frame, text="")
        self.api_status_label.grid(row=2, column=1, padx=(10, 0), sticky=tk.W)
        
        api_frame.columnconfigure(1, weight=1)
        
        # Knowledge Base Section
        kb_frame = ttk.LabelFrame(main_container, text="Knowledge Base Management", padding=15)
        kb_frame.pack(fill=tk.X, pady=(0, 20))
        
        kb_info = ttk.Label(kb_frame, text="Populate the knowledge base with your project documents", style='Header.TLabel')
        kb_info.pack(pady=(0, 10))
        
        kb_buttons_frame = ttk.Frame(kb_frame)
        kb_buttons_frame.pack(fill=tk.X)
        
        populate_btn = ttk.Button(kb_buttons_frame, text="Populate Knowledge Base", 
                                 command=self.populate_knowledge_base, style='Action.TButton')
        populate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = ttk.Button(kb_buttons_frame, text="Refresh KB", 
                                command=self.refresh_knowledge_base, style='Action.TButton')
        refresh_btn.pack(side=tk.LEFT)
        
        # KB Status
        self.kb_status_label = ttk.Label(kb_frame, text="Knowledge base status: Unknown")
        self.kb_status_label.pack(pady=(10, 0), anchor=tk.W)
        
        # Project Structure Section
        structure_frame = ttk.LabelFrame(main_container, text="Project Structure", padding=15)
        structure_frame.pack(fill=tk.BOTH, expand=True)
        
        structure_text = scrolledtext.ScrolledText(structure_frame, height=10, width=80)
        structure_text.pack(fill=tk.BOTH, expand=True)
        
        # Display project structure
        self.display_project_structure(structure_text)
        
    def create_plan_generation_tab(self):
        """Create verification plan generation tab"""
        plan_frame = ttk.Frame(self.notebook)
        self.notebook.add(plan_frame, text="C Verification Plans")
        
        main_container = ttk.Frame(plan_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="C Verification Plan Generation", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Input Section
        input_frame = ttk.LabelFrame(main_container, text="Plan Generation Settings", padding=15)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(input_frame, text="Feature Description:").grid(row=0, column=0, sticky=tk.NW, pady=5)
        self.feature_desc_text = scrolledtext.ScrolledText(input_frame, height=4, width=60)
        self.feature_desc_text.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=(10, 0), pady=5)
        
        ttk.Label(input_frame, text="Specification File (Optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.spec_file_var = tk.StringVar()
        spec_entry = ttk.Entry(input_frame, textvariable=self.spec_file_var, width=50)
        spec_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_spec_btn = ttk.Button(input_frame, text="Browse", command=self.browse_spec_file)
        browse_spec_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Generation Buttons
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill=tk.X, pady=(0, 20))
        
        gen_plan_btn = ttk.Button(buttons_frame, text="Generate Verification Plan", 
                                 command=self.generate_verification_plan, style='Action.TButton')
        gen_plan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        gen_uvm_plan_btn = ttk.Button(buttons_frame, text="Generate UVM Plan", 
                                     command=self.generate_uvm_plan, style='Action.TButton')
        gen_uvm_plan_btn.pack(side=tk.LEFT)
        
        # Results Section
        results_frame = ttk.LabelFrame(main_container, text="Generated Plans", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Plans list with scrollbar
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.plans_listbox = tk.Listbox(list_frame)
        plans_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.plans_listbox.yview)
        self.plans_listbox.configure(yscrollcommand=plans_scrollbar.set)
        
        self.plans_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        plans_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Plan actions
        plan_actions_frame = ttk.Frame(results_frame)
        plan_actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        view_plan_btn = ttk.Button(plan_actions_frame, text="View Plan", command=self.view_selected_plan)
        view_plan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_excel_btn = ttk.Button(plan_actions_frame, text="Export to Excel", command=self.export_plan_to_excel)
        export_excel_btn.pack(side=tk.LEFT)
        
        # Refresh plans list
        self.refresh_plans_list()
        
    def create_test_generation_tab(self):
        """Create test generation tab"""
        test_frame = ttk.Frame(self.notebook)
        self.notebook.add(test_frame, text="C Test Generation")
        
        main_container = ttk.Frame(test_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="C Test Generation", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Input Section
        input_frame = ttk.LabelFrame(main_container, text="Test Generation Settings", padding=15)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(input_frame, text="Verification Plan File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.plan_file_var = tk.StringVar()
        plan_entry = ttk.Entry(input_frame, textvariable=self.plan_file_var, width=50)
        plan_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_plan_btn = ttk.Button(input_frame, text="Browse", command=self.browse_plan_file)
        browse_plan_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        ttk.Label(input_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value="generated_outputs/c_tests")
        output_entry = ttk.Entry(input_frame, textvariable=self.output_dir_var, width=50)
        output_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_output_btn = ttk.Button(input_frame, text="Browse", command=self.browse_output_dir)
        browse_output_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        ttk.Label(input_frame, text="Address Map File (Optional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.addr_map_var = tk.StringVar()
        addr_entry = ttk.Entry(input_frame, textvariable=self.addr_map_var, width=50)
        addr_entry.grid(row=2, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_addr_btn = ttk.Button(input_frame, text="Browse", command=self.browse_addr_map)
        browse_addr_btn.grid(row=2, column=2, padx=(5, 0), pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Generation Button
        gen_tests_btn = ttk.Button(main_container, text="Generate C Tests", 
                                  command=self.generate_c_tests, style='Action.TButton')
        gen_tests_btn.pack(pady=(0, 20))
        
        # Results Section
        results_frame = ttk.LabelFrame(main_container, text="Generated Tests", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tests list
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tests_listbox = tk.Listbox(list_frame)
        tests_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tests_listbox.yview)
        self.tests_listbox.configure(yscrollcommand=tests_scrollbar.set)
        
        self.tests_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tests_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Test actions
        test_actions_frame = ttk.Frame(results_frame)
        test_actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        view_test_btn = ttk.Button(test_actions_frame, text="View Test", command=self.view_selected_test)
        view_test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        regenerate_test_btn = ttk.Button(test_actions_frame, text="Regenerate Test", command=self.regenerate_test)
        regenerate_test_btn.pack(side=tk.LEFT)
        
        # Refresh tests list
        self.refresh_tests_list()
        
    def create_uvm_tab(self):
        """Create UVM generation tab"""
        uvm_frame = ttk.Frame(self.notebook)
        self.notebook.add(uvm_frame, text="UVM Generation")
        
        main_container = ttk.Frame(uvm_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="UVM Test Generation", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # UVM Plan Generation Section
        plan_section = ttk.LabelFrame(main_container, text="UVM Verification Plan Generation", padding=15)
        plan_section.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(plan_section, text="Feature Description:").grid(row=0, column=0, sticky=tk.NW, pady=5)
        self.uvm_feature_text = scrolledtext.ScrolledText(plan_section, height=3, width=60)
        self.uvm_feature_text.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        gen_uvm_plan_btn = ttk.Button(plan_section, text="Generate UVM Plan", 
                                     command=self.generate_uvm_plan, style='Action.TButton')
        gen_uvm_plan_btn.grid(row=1, column=0, columnspan=2, pady=10)
        
        plan_section.columnconfigure(1, weight=1)
        
        # UVM Test Generation Section
        test_section = ttk.LabelFrame(main_container, text="UVM Test Generation", padding=15)
        test_section.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(test_section, text="UVM Plan File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.uvm_plan_file_var = tk.StringVar()
        uvm_plan_entry = ttk.Entry(test_section, textvariable=self.uvm_plan_file_var, width=50)
        uvm_plan_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_uvm_plan_btn = ttk.Button(test_section, text="Browse", command=self.browse_uvm_plan_file)
        browse_uvm_plan_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        ttk.Label(test_section, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.uvm_output_dir_var = tk.StringVar(value="generated_outputs/uvm_tests")
        uvm_output_entry = ttk.Entry(test_section, textvariable=self.uvm_output_dir_var, width=50)
        uvm_output_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_uvm_output_btn = ttk.Button(test_section, text="Browse", command=self.browse_uvm_output_dir)
        browse_uvm_output_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        # Coverage enable checkbox
        self.coverage_enable_var = tk.BooleanVar(value=False)
        coverage_check = ttk.Checkbutton(test_section, text="Enable Comprehensive Coverage", 
                                        variable=self.coverage_enable_var)
        coverage_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        gen_uvm_tests_btn = ttk.Button(test_section, text="Generate UVM Tests", 
                                      command=self.generate_uvm_tests, style='Action.TButton')
        gen_uvm_tests_btn.grid(row=3, column=0, columnspan=3, pady=10)
        
        test_section.columnconfigure(1, weight=1)
        
        # Results Section
        results_frame = ttk.LabelFrame(main_container, text="Generated UVM Files", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # UVM files list
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.uvm_files_listbox = tk.Listbox(list_frame)
        uvm_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.uvm_files_listbox.yview)
        self.uvm_files_listbox.configure(yscrollcommand=uvm_scrollbar.set)
        
        self.uvm_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        uvm_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # UVM actions
        uvm_actions_frame = ttk.Frame(results_frame)
        uvm_actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        view_uvm_btn = ttk.Button(uvm_actions_frame, text="View File", command=self.view_selected_uvm_file)
        view_uvm_btn.pack(side=tk.LEFT)
        
        # Refresh UVM files list
        self.refresh_uvm_files_list()
        
    def create_utilities_tab(self):
        """Create utilities tab"""
        utils_frame = ttk.Frame(self.notebook)
        self.notebook.add(utils_frame, text="Utilities")
        
        main_container = ttk.Frame(utils_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="Utilities & Tools", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # PDF Processing Section
        pdf_frame = ttk.LabelFrame(main_container, text="PDF Processing", padding=15)
        pdf_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(pdf_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pdf_file_var = tk.StringVar()
        pdf_entry = ttk.Entry(pdf_frame, textvariable=self.pdf_file_var, width=50)
        pdf_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_pdf_btn = ttk.Button(pdf_frame, text="Browse", command=self.browse_pdf_file)
        browse_pdf_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Vision analysis checkbox
        self.vision_enable_var = tk.BooleanVar(value=False)
        vision_check = ttk.Checkbutton(pdf_frame, text="Enable AI Vision Analysis", 
                                      variable=self.vision_enable_var)
        vision_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        convert_pdf_btn = ttk.Button(pdf_frame, text="Convert PDF to Markdown", 
                                    command=self.convert_pdf, style='Action.TButton')
        convert_pdf_btn.grid(row=2, column=0, columnspan=3, pady=10)
        
        pdf_frame.columnconfigure(1, weight=1)
        
        # Comprehensive Generation Section
        comp_frame = ttk.LabelFrame(main_container, text="Comprehensive Test Generation", padding=15)
        comp_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(comp_frame, text="Specification File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.comp_spec_var = tk.StringVar()
        comp_spec_entry = ttk.Entry(comp_frame, textvariable=self.comp_spec_var, width=50)
        comp_spec_entry.grid(row=0, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_comp_spec_btn = ttk.Button(comp_frame, text="Browse", command=self.browse_comp_spec)
        browse_comp_spec_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        ttk.Label(comp_frame, text="Memory Map File (Optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.comp_memmap_var = tk.StringVar()
        comp_memmap_entry = ttk.Entry(comp_frame, textvariable=self.comp_memmap_var, width=50)
        comp_memmap_entry.grid(row=1, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_comp_memmap_btn = ttk.Button(comp_frame, text="Browse", command=self.browse_comp_memmap)
        browse_comp_memmap_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        ttk.Label(comp_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.comp_output_var = tk.StringVar(value="generated_outputs/comprehensive_verification")
        comp_output_entry = ttk.Entry(comp_frame, textvariable=self.comp_output_var, width=50)
        comp_output_entry.grid(row=2, column=1, sticky=tk.EW, padx=(10, 0), pady=5)
        
        browse_comp_output_btn = ttk.Button(comp_frame, text="Browse", command=self.browse_comp_output)
        browse_comp_output_btn.grid(row=2, column=2, padx=(5, 0), pady=5)
        
        generate_comp_btn = ttk.Button(comp_frame, text="Generate Comprehensive Tests", 
                                      command=self.generate_comprehensive, style='Action.TButton')
        generate_comp_btn.grid(row=3, column=0, columnspan=3, pady=10)
        
        comp_frame.columnconfigure(1, weight=1)
        
        # Project Statistics Section
        stats_frame = ttk.LabelFrame(main_container, text="Project Statistics", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=8, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        refresh_stats_btn = ttk.Button(stats_frame, text="Refresh Statistics", command=self.refresh_statistics)
        refresh_stats_btn.pack(pady=(10, 0))
        
        # Initial stats load
        self.refresh_statistics()
        
    def create_console_tab(self):
        """Create console output tab"""
        console_frame = ttk.Frame(self.notebook)
        self.notebook.add(console_frame, text="Console Output")
        
        main_container = ttk.Frame(console_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="Console Output & Logs", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        # Console output area
        self.console_text = scrolledtext.ScrolledText(main_container, height=30, width=100, 
                                                     background='black', foreground='white',
                                                     font=('Consolas', 10))
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        # Console controls
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill=tk.X, pady=(10, 0))
        
        clear_console_btn = ttk.Button(controls_frame, text="Clear Console", command=self.clear_console)
        clear_console_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        save_log_btn = ttk.Button(controls_frame, text="Save Log", command=self.save_console_log)
        save_log_btn.pack(side=tk.LEFT)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(controls_frame, text="Auto-scroll", 
                                           variable=self.auto_scroll_var)
        auto_scroll_check.pack(side=tk.RIGHT)
        
    # GUI Event Handlers
    def browse_spec_file(self):
        """Browse for specification file"""
        filename = filedialog.askopenfilename(
            title="Select Specification File",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if filename:
            self.spec_file_var.set(filename)
            
    def browse_plan_file(self):
        """Browse for verification plan file"""
        filename = filedialog.askopenfilename(
            title="Select Verification Plan File",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialdir="generated_outputs/verification_plans"
        )
        if filename:
            self.plan_file_var.set(filename)
            
    def browse_output_dir(self):
        """Browse for output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir_var.set(dirname)
            
    def browse_addr_map(self):
        """Browse for address map file"""
        filename = filedialog.askopenfilename(
            title="Select Address Map File",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="knowledge_base_src/regmaps"
        )
        if filename:
            self.addr_map_var.set(filename)
            
    def browse_uvm_plan_file(self):
        """Browse for UVM plan file"""
        filename = filedialog.askopenfilename(
            title="Select UVM Verification Plan File",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialdir="generated_outputs/uvm_verification_plans"
        )
        if filename:
            self.uvm_plan_file_var.set(filename)
            
    def browse_uvm_output_dir(self):
        """Browse for UVM output directory"""
        dirname = filedialog.askdirectory(title="Select UVM Output Directory")
        if dirname:
            self.uvm_output_dir_var.set(dirname)
            
    def browse_pdf_file(self):
        """Browse for PDF file"""
        filename = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_file_var.set(filename)
            
    def browse_comp_spec(self):
        """Browse for comprehensive spec file"""
        filename = filedialog.askopenfilename(
            title="Select Specification File",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if filename:
            self.comp_spec_var.set(filename)
            
    def browse_comp_memmap(self):
        """Browse for comprehensive memmap file"""
        filename = filedialog.askopenfilename(
            title="Select Memory Map File",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.comp_memmap_var.set(filename)
            
    def browse_comp_output(self):
        """Browse for comprehensive output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.comp_output_var.set(dirname)
    
    # Core functionality methods
    def test_api_connection(self):
        """Test API connection"""
        def test_api():
            try:
                self.log_message("Testing API connection...")
                
                # Set API key and model
                common_utils.OPENROUTER_API_KEY = self.api_key.get()
                common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = self.model_name.get()
                
                # Initialize automator for testing
                automator = ASICVerificationAutomator(
                    api_key=self.api_key.get(),
                    model_name=self.model_name.get()
                )
                
                # Simple test call
                response = automator._call_llm_api("Hello, this is a test. Please respond with 'API connection successful.'", 
                                                 max_tokens=50, temperature=0.1)
                
                if "successful" in response.lower() or "hello" in response.lower():
                    self.output_queue.put(("api_status", "success", "API connection successful!"))
                    self.log_message("✓ API connection test passed")
                else:
                    self.output_queue.put(("api_status", "error", f"Unexpected response: {response[:100]}"))
                    self.log_message(f"⚠ Unexpected API response: {response[:100]}")
                    
            except Exception as e:
                self.output_queue.put(("api_status", "error", f"API connection failed: {str(e)}"))
                self.log_message(f"✗ API connection failed: {str(e)}")
        
        # Run test in background thread
        threading.Thread(target=test_api, daemon=True).start()
        
    def populate_knowledge_base(self):
        """Populate knowledge base"""
        def populate_kb():
            try:
                self.log_message("Starting knowledge base population...")
                
                # Set API configuration
                common_utils.OPENROUTER_API_KEY = self.api_key.get()
                common_utils.DEEPSEEK_MODEL_NAME_DEFAULT = self.model_name.get()
                
                # Run populate_kb script
                result = subprocess.run([
                    sys.executable, "main_orchestrator.py", "populate_kb",
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ], capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.output_queue.put(("kb_status", "success", "Knowledge base populated successfully!"))
                    self.log_message("✓ Knowledge base population completed")
                    self.log_message(result.stdout)
                else:
                    self.output_queue.put(("kb_status", "error", f"Population failed: {result.stderr}"))
                    self.log_message(f"✗ Knowledge base population failed: {result.stderr}")
                    
            except Exception as e:
                self.output_queue.put(("kb_status", "error", f"Population error: {str(e)}"))
                self.log_message(f"✗ Knowledge base population error: {str(e)}")
        
        threading.Thread(target=populate_kb, daemon=True).start()
        
    def refresh_knowledge_base(self):
        """Refresh knowledge base"""
        self.populate_knowledge_base()  # Same as populate for now
        
    def generate_verification_plan(self):
        """Generate verification plan"""
        feature_desc = self.feature_desc_text.get("1.0", tk.END).strip()
        if not feature_desc:
            messagebox.showerror("Error", "Please enter a feature description")
            return
            
        def generate_plan():
            try:
                self.log_message(f"Generating verification plan for: {feature_desc}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "gen_plan",
                    feature_desc,
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ Verification plan generated successfully")
                    self.log_message(result.stdout)
                    self.refresh_plans_list()
                else:
                    self.log_message(f"✗ Plan generation failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ Plan generation error: {str(e)}")
        
        threading.Thread(target=generate_plan, daemon=True).start()
        
    def generate_uvm_plan(self):
        """Generate UVM verification plan"""
        feature_desc = self.uvm_feature_text.get("1.0", tk.END).strip()
        if not feature_desc:
            messagebox.showerror("Error", "Please enter a feature description")
            return
            
        def generate_plan():
            try:
                self.log_message(f"Generating UVM verification plan for: {feature_desc}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "gen_uvm_plan",
                    feature_desc,
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ UVM verification plan generated successfully")
                    self.log_message(result.stdout)
                    self.refresh_uvm_files_list()
                else:
                    self.log_message(f"✗ UVM plan generation failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ UVM plan generation error: {str(e)}")
        
        threading.Thread(target=generate_plan, daemon=True).start()
        
    def generate_c_tests(self):
        """Generate C tests"""
        plan_file = self.plan_file_var.get()
        if not plan_file:
            messagebox.showerror("Error", "Please select a verification plan file")
            return
            
        def generate_tests():
            try:
                self.log_message(f"Generating C tests from plan: {plan_file}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "gen_tests",
                    "--plan_file", plan_file,
                    "--output-dir", self.output_dir_var.get(),
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                if self.addr_map_var.get():
                    cmd.extend(["--addr_map_file", self.addr_map_var.get()])
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ C tests generated successfully")
                    self.log_message(result.stdout)
                    self.refresh_tests_list()
                else:
                    self.log_message(f"✗ C test generation failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ C test generation error: {str(e)}")
        
        threading.Thread(target=generate_tests, daemon=True).start()
        
    def generate_uvm_tests(self):
        """Generate UVM tests"""
        plan_file = self.uvm_plan_file_var.get()
        if not plan_file:
            messagebox.showerror("Error", "Please select a UVM verification plan file")
            return
            
        def generate_tests():
            try:
                self.log_message(f"Generating UVM tests from plan: {plan_file}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "gen_uvm_tests",
                    plan_file,
                    "--output", self.uvm_output_dir_var.get(),
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                if self.coverage_enable_var.get():
                    cmd.append("--coverage_enable")
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ UVM tests generated successfully")
                    self.log_message(result.stdout)
                    self.refresh_uvm_files_list()
                else:
                    self.log_message(f"✗ UVM test generation failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ UVM test generation error: {str(e)}")
        
        threading.Thread(target=generate_tests, daemon=True).start()
        
    def convert_pdf(self):
        """Convert PDF to markdown"""
        pdf_file = self.pdf_file_var.get()
        if not pdf_file:
            messagebox.showerror("Error", "Please select a PDF file")
            return
            
        def convert():
            try:
                self.log_message(f"Converting PDF: {pdf_file}")
                
                cmd = [sys.executable, "convert_pdfs.py", pdf_file]
                if self.vision_enable_var.get():
                    cmd.append("--vision")
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ PDF converted successfully")
                    self.log_message(result.stdout)
                else:
                    self.log_message(f"✗ PDF conversion failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ PDF conversion error: {str(e)}")
        
        threading.Thread(target=convert, daemon=True).start()
        
    def generate_comprehensive(self):
        """Generate comprehensive tests"""
        spec_file = self.comp_spec_var.get()
        if not spec_file:
            messagebox.showerror("Error", "Please select a specification file")
            return
            
        def generate():
            try:
                self.log_message(f"Generating comprehensive tests from: {spec_file}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "generate_comprehensive",
                    spec_file,
                    "--output_dir", self.comp_output_var.get(),
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get(),
                    "--verbose"
                ]
                
                if self.comp_memmap_var.get():
                    cmd.extend(["--memmap_file", self.comp_memmap_var.get()])
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ Comprehensive tests generated successfully")
                    self.log_message(result.stdout)
                else:
                    self.log_message(f"✗ Comprehensive generation failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ Comprehensive generation error: {str(e)}")
        
        threading.Thread(target=generate, daemon=True).start()
        
    # Utility methods
    def refresh_plans_list(self):
        """Refresh the verification plans list"""
        try:
            self.plans_listbox.delete(0, tk.END)
            plans_dir = Path("generated_outputs/verification_plans")
            if plans_dir.exists():
                for plan_file in plans_dir.glob("*.md"):
                    self.plans_listbox.insert(tk.END, plan_file.name)
        except Exception as e:
            self.log_message(f"Error refreshing plans list: {str(e)}")
            
    def refresh_tests_list(self):
        """Refresh the C tests list"""
        try:
            self.tests_listbox.delete(0, tk.END)
            tests_dir = Path(self.output_dir_var.get())
            if tests_dir.exists():
                for test_file in tests_dir.glob("*.c"):
                    self.tests_listbox.insert(tk.END, test_file.name)
        except Exception as e:
            self.log_message(f"Error refreshing tests list: {str(e)}")
            
    def refresh_uvm_files_list(self):
        """Refresh the UVM files list"""
        try:
            self.uvm_files_listbox.delete(0, tk.END)
            
            # Add UVM plans
            plans_dir = Path("generated_outputs/uvm_verification_plans")
            if plans_dir.exists():
                for plan_file in plans_dir.glob("*.md"):
                    self.uvm_files_listbox.insert(tk.END, f"[PLAN] {plan_file.name}")
            
            # Add UVM tests
            tests_dir = Path(self.uvm_output_dir_var.get())
            if tests_dir.exists():
                for test_file in tests_dir.glob("*.sv"):
                    self.uvm_files_listbox.insert(tk.END, f"[TEST] {test_file.name}")
                    
        except Exception as e:
            self.log_message(f"Error refreshing UVM files list: {str(e)}")
            
    def view_selected_plan(self):
        """View selected verification plan"""
        selection = self.plans_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a plan to view")
            return
            
        plan_name = self.plans_listbox.get(selection[0])
        plan_path = Path("generated_outputs/verification_plans") / plan_name
        
        self.view_file(plan_path)
        
    def view_selected_test(self):
        """View selected test file"""
        selection = self.tests_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a test to view")
            return
            
        test_name = self.tests_listbox.get(selection[0])
        test_path = Path(self.output_dir_var.get()) / test_name
        
        self.view_file(test_path)
        
    def view_selected_uvm_file(self):
        """View selected UVM file"""
        selection = self.uvm_files_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to view")
            return
            
        file_entry = self.uvm_files_listbox.get(selection[0])
        
        if file_entry.startswith("[PLAN]"):
            file_name = file_entry[7:]  # Remove "[PLAN] " prefix
            file_path = Path("generated_outputs/uvm_verification_plans") / file_name
        elif file_entry.startswith("[TEST]"):
            file_name = file_entry[7:]  # Remove "[TEST] " prefix
            file_path = Path(self.uvm_output_dir_var.get()) / file_name
        else:
            messagebox.showerror("Error", "Unknown file type")
            return
            
        self.view_file(file_path)
        
    def view_file(self, file_path):
        """View file in a new window"""
        try:
            if not file_path.exists():
                messagebox.showerror("Error", f"File not found: {file_path}")
                return
                
            # Create new window
            view_window = tk.Toplevel(self.root)
            view_window.title(f"Viewing: {file_path.name}")
            view_window.geometry("800x600")
            
            # Create text widget with scrollbar
            text_frame = ttk.Frame(view_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # Load and display file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                text_widget.insert(tk.END, content)
                
            text_widget.config(state=tk.DISABLED)  # Make read-only
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
            
    def regenerate_test(self):
        """Regenerate selected test"""
        selection = self.tests_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a test to regenerate")
            return
            
        test_name = self.tests_listbox.get(selection[0])
        test_path = Path(self.output_dir_var.get()) / test_name
        
        def regenerate():
            try:
                self.log_message(f"Regenerating test: {test_name}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "regenerate_test",
                    "--test_file", str(test_path),
                    "--plan_file", self.plan_file_var.get(),
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ Test regenerated successfully")
                    self.log_message(result.stdout)
                else:
                    self.log_message(f"✗ Test regeneration failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ Test regeneration error: {str(e)}")
        
        threading.Thread(target=regenerate, daemon=True).start()
        
    def export_plan_to_excel(self):
        """Export selected plan to Excel"""
        selection = self.plans_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a plan to export")
            return
            
        plan_name = self.plans_listbox.get(selection[0])
        plan_path = Path("generated_outputs/verification_plans") / plan_name
        
        # Ask for Excel file location
        excel_file = filedialog.asksaveasfilename(
            title="Save Excel Report",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialdir="generated_outputs/excel_reports"
        )
        
        if not excel_file:
            return
            
        def export():
            try:
                self.log_message(f"Exporting plan to Excel: {excel_file}")
                
                cmd = [
                    sys.executable, "main_orchestrator.py", "plan_to_excel",
                    "--plan_file", str(plan_path),
                    "--excel_file", excel_file,
                    "--openrouter-key", self.api_key.get(),
                    "--llm-model", self.model_name.get()
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT_DIR)
                
                if result.returncode == 0:
                    self.log_message("✓ Plan exported to Excel successfully")
                    self.log_message(result.stdout)
                else:
                    self.log_message(f"✗ Excel export failed: {result.stderr}")
                    
            except Exception as e:
                self.log_message(f"✗ Excel export error: {str(e)}")
        
        threading.Thread(target=export, daemon=True).start()
        
    def refresh_statistics(self):
        """Refresh project statistics"""
        try:
            stats = []
            
            # Count files in various directories
            plans_dir = Path("generated_outputs/verification_plans")
            if plans_dir.exists():
                plan_count = len(list(plans_dir.glob("*.md")))
                stats.append(f"Verification Plans: {plan_count}")
            
            c_tests_dir = Path("generated_outputs/c_tests")
            if c_tests_dir.exists():
                c_test_count = len(list(c_tests_dir.glob("*.c")))
                stats.append(f"C Test Files: {c_test_count}")
            
            uvm_plans_dir = Path("generated_outputs/uvm_verification_plans")
            if uvm_plans_dir.exists():
                uvm_plan_count = len(list(uvm_plans_dir.glob("*.md")))
                stats.append(f"UVM Verification Plans: {uvm_plan_count}")
            
            uvm_tests_dir = Path("generated_outputs/uvm_tests")
            if uvm_tests_dir.exists():
                uvm_test_count = len(list(uvm_tests_dir.glob("*.sv")))
                stats.append(f"UVM Test Files: {uvm_test_count}")
            
            # Knowledge base statistics
            kb_dirs = ["specs", "hal", "regmaps", "c_test_examples", "uvm_examples"]
            kb_stats = []
            for kb_dir in kb_dirs:
                kb_path = Path("knowledge_base_src") / kb_dir
                if kb_path.exists():
                    file_count = len(list(kb_path.rglob("*.*")))
                    kb_stats.append(f"  {kb_dir}: {file_count} files")
            
            if kb_stats:
                stats.append("\\nKnowledge Base:")
                stats.extend(kb_stats)
            
            # Vector database info
            vector_db_path = Path("vector_db")
            if vector_db_path.exists():
                try:
                    db_size = sum(f.stat().st_size for f in vector_db_path.rglob('*') if f.is_file())
                    db_size_mb = db_size / (1024 * 1024)
                    stats.append(f"\\nVector Database Size: {db_size_mb:.1f} MB")
                except:
                    stats.append("\\nVector Database: Present")
            
            # Display statistics
            stats_text = "\\n".join(stats)
            stats_text += f"\\n\\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert(tk.END, stats_text)
            
        except Exception as e:
            self.log_message(f"Error refreshing statistics: {str(e)}")
            
    def display_project_structure(self, text_widget):
        """Display project structure in text widget"""
        structure = """
asic_verification_automation/
├── knowledge_base_src/       # User raw documents
│   ├── specs/                # ASIC specification documents
│   ├── hal/                  # HAL documentation, .h files
│   ├── regmaps/              # Register map details
│   ├── c_test_examples/      # Example C test files
│   └── uvm_examples/         # UVM sequence examples
├── generated_outputs/
│   ├── verification_plans/   # Generated verification plans (C)
│   ├── c_tests/              # Generated C test files
│   ├── uvm_verification_plans/  # UVM verification plans
│   ├── uvm_tests/            # Generated UVM test files
│   └── excel_reports/        # Excel format reports
├── scripts/                  # Core agent scripts
├── vector_db/                # Database
└── gui_app.py                # This GUI application

Usage Instructions:
1. Configure API key in Setup tab
2. Populate knowledge base with your documents
3. Generate verification plans from feature descriptions
4. Generate test code from verification plans
5. Use utilities for PDF conversion and comprehensive generation (unstable!)

For batch/command-line usage, use main_orchestrator.py
        """
        text_widget.insert(tk.END, structure)
        text_widget.config(state=tk.DISABLED)
        
    def log_message(self, message):
        """Log message to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\\n"
        
        self.console_text.insert(tk.END, formatted_message)
        
        if self.auto_scroll_var.get():
            self.console_text.see(tk.END)
            
    def clear_console(self):
        """Clear console output"""
        self.console_text.delete("1.0", tk.END)
        
    def save_console_log(self):
        """Save console log to file"""
        log_file = filedialog.asksaveasfilename(
            title="Save Console Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if log_file:
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(self.console_text.get("1.0", tk.END))
                messagebox.showinfo("Success", f"Console log saved to {log_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save log: {str(e)}")
                
    def monitor_output(self):
        """Monitor output queue for status updates"""
        try:
            while True:
                msg_type, status, message = self.output_queue.get_nowait()
                
                if msg_type == "api_status":
                    if status == "success":
                        self.api_status_label.config(text=message, style='Success.TLabel')
                    else:
                        self.api_status_label.config(text=message, style='Error.TLabel')
                elif msg_type == "kb_status":
                    if status == "success":
                        self.kb_status_label.config(text=message, style='Success.TLabel')
                    else:
                        self.kb_status_label.config(text=message, style='Error.TLabel')
                        
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.monitor_output)


def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = ASICVerificationGUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()
