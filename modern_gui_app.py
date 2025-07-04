import flet as ft
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime
import threading

PROJECT_ROOT_DIR = Path(__file__).resolve().parent
# Ensure main_orchestrator and scripts are discoverable
if str(PROJECT_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIR))

# Attempt to import common_utils for default model name, fallback if not found
try:
    from scripts import common_utils
    DEFAULT_MODEL_NAME = common_utils.DEEPSEEK_MODEL_NAME_DEFAULT
except ImportError:
    DEFAULT_MODEL_NAME = "deepseek/deepseek-chat" # Fallback

class ModernApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "genToast: Modern ASIC Verification Agent"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH # Stretch to fill width
        self.page.theme_mode = ft.ThemeMode.LIGHT # Or ft.ThemeMode.DARK
        self.page.padding = 0 # Remove default page padding, manage with containers

        # --- Centralized File Pickers ---
        self.spec_file_picker = ft.FilePicker(on_result=self._on_spec_file_picked)
        self.c_plan_file_picker = ft.FilePicker(on_result=self._on_c_plan_file_picked)
        self.output_dir_picker = ft.FilePicker(on_result=self._on_output_dir_picked) # For directories
        self.excel_save_file_picker = ft.FilePicker(on_result=self._on_excel_save_file_picked)
        self.log_save_file_picker = ft.FilePicker(on_result=self._on_log_save_file_picked)

        self.page.overlay.extend([
            self.spec_file_picker, 
            self.c_plan_file_picker, 
            self.output_dir_picker,
            self.excel_save_file_picker,
            self.log_save_file_picker
        ])

        # --- UI Controls ---
        # Setup Tab
        self.api_key_field = ft.TextField(
            label="OpenRouter API Key", password=True, can_reveal_password=True, 
            value=os.getenv('OPENROUTER_API_KEY', ''), width=400
        )
        self.model_name_field = ft.TextField(
            label="LLM Model Name", value=DEFAULT_MODEL_NAME, width=400
        )
        self.api_status_label = ft.Text("API Status: Unknown", weight=ft.FontWeight.BOLD)
        self.kb_status_label = ft.Text("Knowledge Base Status: Unknown", weight=ft.FontWeight.BOLD)        
        self.project_structure_display = ft.TextField(
            label="Project Structure", multiline=True, read_only=True, min_lines=8, max_lines=15,
            value="Loading project structure..."
        )

        # C Verification Plans Tab
        self.feature_desc_text = ft.TextField(label="Feature Description", multiline=True, min_lines=3, max_lines=5)
        self.spec_file_path_text = ft.TextField(label="Specification File (Optional)", read_only=True, hint_text="Select a spec file...")
        self.c_plans_list_lv = ft.ListView(spacing=5, auto_scroll=False, expand=True)
        self.selected_c_plan_path: Path | None = None # To store path of selected plan

        # Console
        self.console_log_lv = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self.auto_scroll_checkbox = ft.Checkbox(label="Auto-scroll console", value=True)

        # C Tests Tab
        self.c_plan_for_tests_path_text = ft.TextField(label="Verification Plan File", read_only=True, hint_text="Select a C plan file...")
        self.c_tests_output_dir_text = ft.TextField(label="Output Directory", value="generated_outputs/c_tests")
        self.addr_map_file_text = ft.TextField(label="Address Map File (Optional)", read_only=True, hint_text="Select address map file...")
        self.c_tests_list_lv = ft.ListView(spacing=5, auto_scroll=False, expand=True)
        self.selected_c_test_path: Path | None = None

        # UVM Tab
        self.uvm_feature_desc_text = ft.TextField(label="Feature Description (for UVM Plan)", multiline=True, min_lines=3, max_lines=5)
        self.uvm_plan_file_text = ft.TextField(label="UVM Plan File", read_only=True, hint_text="Select a UVM plan file...")
        self.uvm_output_dir_text = ft.TextField(label="UVM Output Directory", value="generated_outputs/uvm_tests")
        self.coverage_enable_checkbox = ft.Checkbox(label="Enable Comprehensive Coverage", value=False)
        self.uvm_files_list_lv = ft.ListView(spacing=5, auto_scroll=False, expand=True)
        self.selected_uvm_file_path: Path | None = None

        # Utilities Tab
        self.pdf_file_text = ft.TextField(label="PDF File", read_only=True, hint_text="Select a PDF file...")
        self.vision_enable_checkbox = ft.Checkbox(label="Enable AI Vision Analysis", value=False)
        self.comp_spec_file_text = ft.TextField(label="Specification File", read_only=True, hint_text="Select specification file...")
        self.comp_memmap_file_text = ft.TextField(label="Memory Map File (Optional)", read_only=True, hint_text="Select memory map file...")
        self.comp_output_dir_text = ft.TextField(label="Output Directory", value="generated_outputs/comprehensive_verification")

        self.build_ui()
        self.display_project_structure() # Initial population
        self.refresh_c_plans_list() # Initial population
        self.refresh_c_tests_list() # Initial population
        self.refresh_uvm_files_list() # Initial population

    def log_message(self, message: str, category: str = "INFO", color: str = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        log_colors = {
            "INFO": ft.Colors.BLUE_GREY_300,
            "SUCCESS": ft.Colors.GREEN_ACCENT_700,
            "ERROR": ft.Colors.RED_ACCENT_700,
            "WARNING": ft.Colors.AMBER_ACCENT_700,
            "CMD": ft.Colors.PURPLE_ACCENT_100,
            "OUTPUT": ft.Colors.GREY_500
        }
        
        final_color = color if color else log_colors.get(category.upper(), ft.Colors.WHITE)

        # Remove previous 'last' marker if it exists
        if self.console_log_lv.controls and hasattr(self.console_log_lv.controls[-1], 'key') and self.console_log_lv.controls[-1].key == 'last':
            self.console_log_lv.controls.pop()

        self.console_log_lv.controls.append(
            ft.Text(f"[{timestamp}][{category}] {message}", color=final_color, font_family="monospace", size=12, selectable=True)
        )
        
        # Add a new 'last' marker for scrolling
        # Ensure it's a unique object if Flet has issues with identical keys, though 'key' string should be fine.
        self.console_log_lv.controls.append(ft.Container(content=None, key='last', height=0, width=0, padding=0, margin=0))


        if self.auto_scroll_checkbox.value:
            # self.page.update() # Update before scroll might be needed if list was empty or structure changed significantly
            self.console_log_lv.scroll_to(key='last', duration=100, curve=ft.AnimationCurve.EASE_IN_OUT)
        
        self.page.update()


    def run_orchestrator_command_threaded(self, command_args: list, success_msg: str, error_msg_prefix: str, status_label: ft.Text = None, on_complete_callback=None):
        def task():
            self.log_message(f"Running: main_orchestrator.py {' '.join(command_args)}", category="CMD")
            if status_label:
                status_label.value = f"{error_msg_prefix}: Running..."
                status_label.color = ft.Colors.BLUE_500
                status_label.update()

            try:
                process = subprocess.Popen(
                    [sys.executable, str(PROJECT_ROOT_DIR / "main_orchestrator.py")] + command_args,
                    cwd=PROJECT_ROOT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8', # Specify encoding
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # Log stdout
                for line in iter(process.stdout.readline, ''):
                    self.log_message(line.strip(), category="OUTPUT")
                process.stdout.close()

                # Log stderr
                error_output = []
                for line in iter(process.stderr.readline, ''):
                    self.log_message(line.strip(), category="ERROR")
                    error_output.append(line.strip())
                process.stderr.close()
                
                process.wait()

                if process.returncode == 0:
                    self.log_message(success_msg, category="SUCCESS")
                    if status_label:
                        status_label.value = f"{error_msg_prefix}: {success_msg.split(':')[0]}"
                        status_label.color = ft.Colors.GREEN_ACCENT_700
                else:
                    err_summary = " ".join(error_output) if error_output else "Unknown error."
                    self.log_message(f"{error_msg_prefix} failed. RC: {process.returncode}. Error: {err_summary}", category="ERROR")
                    if status_label:
                        status_label.value = f"{error_msg_prefix}: Failed (RC {process.returncode})"
                        status_label.color = ft.Colors.RED_ACCENT_700
            except Exception as e:
                self.log_message(f"Exception during '{error_msg_prefix}': {str(e)}", category="ERROR")
                if status_label:
                    status_label.value = f"{error_msg_prefix}: Exception"
                    status_label.color = ft.Colors.RED_ACCENT_700
            finally:
                if status_label: status_label.update()
                if on_complete_callback: on_complete_callback()
                self.page.update()
        
        threading.Thread(target=task, daemon=True).start()

    # --- Setup Tab Methods ---
    def test_api_connection(self, e):
        api_key = self.api_key_field.value
        model_name = self.model_name_field.value
        if not api_key:
            self.log_message("API Key is required for testing connection.", category="WARNING")
            self.api_status_label.value = "API Status: API Key missing"
            self.api_status_label.color = ft.Colors.AMBER_ACCENT_700
            self.api_status_label.update()
            return
        
        # This command 'test_connection' needs to exist in main_orchestrator.py
        # It should ideally perform a lightweight operation like listing models or a small query.
        self.run_orchestrator_command_threaded(
            ["test_connection", "--openrouter-key", api_key, "--llm-model", model_name],
            "API Connection Successful!",
            "API Connection Test",
            self.api_status_label
        )

    def populate_kb(self, e):
        self.run_orchestrator_command_threaded(
            ["populate_kb", "--openrouter-key", self.api_key_field.value, "--llm-model", self.model_name_field.value],
            "Knowledge Base Populated Successfully!",
            "KB Population",
            self.kb_status_label
        )

    def refresh_kb(self, e):
        self.run_orchestrator_command_threaded(
            ["populate_kb", "--force-repopulate", "--openrouter-key", self.api_key_field.value, "--llm-model", self.model_name_field.value],
            "Knowledge Base Refreshed Successfully!",
            "KB Refresh",
            self.kb_status_label
        )

    def display_project_structure(self):
        structure = """
asic_verification_automation/
├── knowledge_base_src/
│   ├── specs/, hal/, regmaps/, ...
├── generated_outputs/
│   ├── verification_plans/, c_tests/, ...
├── scripts/
├── vector_db/
├── gui_app.py (Tkinter GUI)
└── modern_gui_app.py (This Flet GUI)

Usage:
1. Setup API Key & Model.
2. Populate/Refresh Knowledge Base.
3. Use other tabs to generate plans & tests.
        """
        self.project_structure_display.value = structure.strip()
        if self.page.controls: self.page.update()


    # --- C Verification Plans Tab Methods ---
    def _on_spec_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            self.spec_file_path_text.value = e.files[0].path
            self.log_message(f"Spec file selected: {e.files[0].path}", category="INFO")
        else:
            self.spec_file_path_text.value = ""
        self.spec_file_path_text.update()

    def _on_c_plan_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            # For C Tests tab - selecting a plan to generate tests from
            self.c_plan_for_tests_path_text.value = e.files[0].path
            self.log_message(f"C plan file selected for test generation: {e.files[0].path}", category="INFO")
            self.c_plan_for_tests_path_text.update()
        else:
            self.c_plan_for_tests_path_text.value = ""
            self.c_plan_for_tests_path_text.update()
            self.log_message("C plan file picking cancelled or no file selected.", category="INFO")

    def _on_output_dir_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            # This could be used by multiple tabs, so we need to determine context
            # For now, we'll handle it generically and let specific methods use it
            self.log_message(f"Output directory selected: {e.path}", category="INFO")
            # The specific handler method will update the appropriate field
        else:
            self.log_message("Output directory selection cancelled.", category="INFO")

    def browse_spec_file(self, e):
        self.spec_file_picker.pick_files(
            dialog_title="Select Specification File",
            allowed_extensions=["txt", "md", "pdf", "docx", "doc"], # Adjust as needed
            allow_multiple=False
        )
    
    def generate_c_verification_plan(self, e):
        feature_desc = self.feature_desc_text.value
        spec_file = self.spec_file_path_text.value

        if not feature_desc:
            self.log_message("Feature description is required to generate C verification plan.", category="WARNING")
            # Optionally show a dialog: self.page.show_dialog(...)
            return

        cmd_args = ["gen_plan", "--feature", feature_desc, 
                    "--openrouter-key", self.api_key_field.value, 
                    "--llm-model", self.model_name_field.value]
        if spec_file:
            cmd_args.extend(["--spec_file", spec_file])
        
        self.run_orchestrator_command_threaded(
            cmd_args,
            "C Verification Plan Generated Successfully!",
            "C Plan Generation",
            on_complete_callback=self.refresh_c_plans_list
        )

    def generate_uvm_verification_plan_from_c_tab(self, e): # Renamed to avoid conflict if UVM tab has similar
        feature_desc = self.feature_desc_text.value # Using same feature desc as C plan for now
        spec_file = self.spec_file_path_text.value # Using same spec file

        if not feature_desc:
            self.log_message("Feature description is required to generate UVM verification plan.", category="WARNING")
            return

        cmd_args = ["gen_uvm_plan", "--feature", feature_desc,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value]
        if spec_file:
            cmd_args.extend(["--spec_file", spec_file])
        
        self.run_orchestrator_command_threaded(
            cmd_args,
            "UVM Verification Plan Generated Successfully!",
            "UVM Plan Generation (from C Tab)",
            # on_complete_callback=self.refresh_uvm_plans_list # If UVM plans are listed elsewhere
        )
        self.log_message("Note: UVM plans are typically managed in the UVM tab.", category="INFO")


    def refresh_c_plans_list(self):
        self.c_plans_list_lv.controls.clear()
        plans_dir = PROJECT_ROOT_DIR / "generated_outputs" / "verification_plans"
        if plans_dir.exists():
            for item in sorted(plans_dir.iterdir()):
                if item.is_file() and item.suffix == '.md':
                    plan_control = ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=ft.Colors.BLUE_GREY_300), ft.Text(item.name, overflow=ft.TextOverflow.ELLIPSIS)], spacing=5),
                        tooltip=f"View or manage {item.name}",
                        on_click=lambda _, p=item: self._select_c_plan(p),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                    )
                    self.c_plans_list_lv.controls.append(plan_control)
        if not self.c_plans_list_lv.controls:
            self.c_plans_list_lv.controls.append(ft.Text("No C verification plans found.", italic=True, color=ft.Colors.GREY_500))
        self.c_plans_list_lv.update()

    def _select_c_plan(self, plan_path: Path):
        self.selected_c_plan_path = plan_path
        self.log_message(f"Selected C plan: {plan_path.name}", category="INFO")
        # Highlight selected item? Flet ListView doesn't have simple selection model like Tkinter.
        # For now, just store it. Buttons will use self.selected_c_plan_path.
        # Could change background of the clicked TextButton temporarily if needed.

    def view_selected_c_plan(self, e):
        if not self.selected_c_plan_path:
            self.log_message("No C plan selected to view.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a plan from the list first."), open=True))
            return
        self.view_file_dialog(self.selected_c_plan_path)

    def _on_excel_save_file_picked(self, e: ft.FilePickerResultEvent):
        if e.path: # For saving, e.path is the chosen path
            excel_file_path = e.path
            if not self.selected_c_plan_path:
                self.log_message("Error: No C plan was selected for export.", category="ERROR")
                return

            self.log_message(f"Exporting {self.selected_c_plan_path.name} to {excel_file_path}", category="INFO")
            cmd_args = [
                "plan_to_excel",
                "--plan_file", str(self.selected_c_plan_path),
                "--excel_file", excel_file_path,
                "--openrouter-key", self.api_key_field.value,
                "--llm-model", self.model_name_field.value
            ]
            self.run_orchestrator_command_threaded(
                cmd_args,
                f"Plan exported to Excel: {Path(excel_file_path).name}",
                "Excel Export"
            )
        else:
            self.log_message("Excel export cancelled or no file selected.", category="INFO")


    def export_c_plan_to_excel(self, e):
        if not self.selected_c_plan_path:
            self.log_message("No C plan selected to export.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a plan from the list first."), open=True))
            return
        
        # Ensure the default directory exists
        default_excel_dir = PROJECT_ROOT_DIR / "generated_outputs" / "excel_reports"
        default_excel_dir.mkdir(parents=True, exist_ok=True)

        self.excel_save_file_picker.save_file(
            dialog_title="Save Excel Report As...",
            file_name=f"{self.selected_c_plan_path.stem}.xlsx",
            initial_directory=str(default_excel_dir),
            allowed_extensions=["xlsx"]
        )
        
    def view_file_dialog(self, file_path: Path):
        try:
            content = file_path.read_text(encoding='utf-8')
            
            dialog_content = ft.Column(
                [
                    ft.TextField(value=content, multiline=True, read_only=True, expand=True, border=ft.InputBorder.NONE, font_family="monospace")
                ],
                tight=True, # Make column take minimum space needed by children
                scroll=ft.ScrollMode.ADAPTIVE, # Allow content to scroll if it's too long
                height=self.page.height * 0.7, # Limit height
                width=self.page.width * 0.8
            )

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Viewing: {file_path.name}"),
                content=dialog_content,
                actions=[ft.TextButton("Close", on_click=lambda _: self.close_dialog(dlg))],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        except Exception as ex:
            self.log_message(f"Error reading file {file_path.name}: {ex}", category="ERROR")
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"Error opening file: {ex}"), open=True))

    def close_dialog(self, dlg: ft.AlertDialog):
        dlg.open = False
        self.page.update()

    # --- C Tests Tab Methods ---
    def browse_c_plan_for_tests(self, e):
        self.c_plan_file_picker.pick_files(
            dialog_title="Select C Verification Plan File",
            allowed_extensions=["md", "txt"],
            allow_multiple=False
        )

    def browse_c_tests_output_dir(self, e):
        self.output_dir_picker.get_directory_path(dialog_title="Select C Tests Output Directory")

    def browse_addr_map_file(self, e):
        # Need a separate file picker for address map files
        addr_map_picker = ft.FilePicker(on_result=self._on_addr_map_file_picked)
        self.page.overlay.append(addr_map_picker)
        self.page.update()
        addr_map_picker.pick_files(
            dialog_title="Select Address Map File",
            allowed_extensions=["txt", "csv", "json"],
            allow_multiple=False
        )

    def _on_addr_map_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            self.addr_map_file_text.value = e.files[0].path
            self.log_message(f"Address map file selected: {e.files[0].path}", category="INFO")
        else:
            self.addr_map_file_text.value = ""
        self.addr_map_file_text.update()

    def generate_c_tests(self, e):
        plan_file = self.c_plan_for_tests_path_text.value
        output_dir = self.c_tests_output_dir_text.value
        addr_map = self.addr_map_file_text.value

        if not plan_file:
            self.log_message("Verification plan file is required to generate C tests.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a verification plan file first."), open=True))
            return

        cmd_args = ["gen_tests", plan_file, "--output", output_dir,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value]
        if addr_map:
            cmd_args.extend(["--address_map", addr_map])

        self.run_orchestrator_command_threaded(
            cmd_args,
            "C Tests Generated Successfully!",
            "C Tests Generation",
            on_complete_callback=self.refresh_c_tests_list
        )

    def refresh_c_tests_list(self):
        self.c_tests_list_lv.controls.clear()
        tests_dir = Path(self.c_tests_output_dir_text.value)
        if tests_dir.exists():
            for item in sorted(tests_dir.iterdir()):
                if item.is_file() and item.suffix == '.c':
                    test_control = ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.CODE, color=ft.Colors.GREEN_ACCENT_400), ft.Text(item.name, overflow=ft.TextOverflow.ELLIPSIS)], spacing=5),
                        tooltip=f"View or manage {item.name}",
                        on_click=lambda _, p=item: self._select_c_test(p),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                    )
                    self.c_tests_list_lv.controls.append(test_control)
        if not self.c_tests_list_lv.controls:
            self.c_tests_list_lv.controls.append(ft.Text("No C test files found.", italic=True, color=ft.Colors.GREY_500))
        self.c_tests_list_lv.update()

    def _select_c_test(self, test_path: Path):
        self.selected_c_test_path = test_path
        self.log_message(f"Selected C test: {test_path.name}", category="INFO")

    def view_selected_c_test(self, e):
        if not self.selected_c_test_path:
            self.log_message("No C test selected to view.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a test from the list first."), open=True))
            return
        self.view_file_dialog(self.selected_c_test_path)

    def regenerate_selected_c_test(self, e):
        if not self.selected_c_test_path:
            self.log_message("No C test selected to regenerate.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a test from the list first."), open=True))
            return

        plan_file = self.c_plan_for_tests_path_text.value
        if not plan_file:
            self.log_message("Plan file is required to regenerate test.", category="WARNING")
            return

        cmd_args = ["regenerate_test", "--test_file", str(self.selected_c_test_path),
                    "--plan_file", plan_file,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value]

        self.run_orchestrator_command_threaded(
            cmd_args,
            f"C Test {self.selected_c_test_path.name} Regenerated Successfully!",
            "C Test Regeneration",
            on_complete_callback=self.refresh_c_tests_list
        )


    # --- UVM Tab Methods ---
    def browse_uvm_plan_file(self, e):
        self.c_plan_file_picker.pick_files(
            dialog_title="Select UVM Plan File",
            allowed_extensions=["md", "txt"],
            allow_multiple=False
        )

    def browse_uvm_output_dir(self, e):
        self.output_dir_picker.get_directory_path(dialog_title="Select UVM Output Directory")

    def generate_uvm_tests(self, e):
        plan_file = self.uvm_plan_file_text.value
        output_dir = self.uvm_output_dir_text.value

        if not plan_file:
            self.log_message("UVM plan file is required to generate UVM tests.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a UVM plan file first."), open=True))
            return

        cmd_args = ["gen_uvm_tests", plan_file, "--output", output_dir,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value]

        self.run_orchestrator_command_threaded(
            cmd_args,
            "UVM Tests Generated Successfully!",
            "UVM Tests Generation",
            on_complete_callback=self.refresh_uvm_files_list
        )

    def refresh_uvm_files_list(self):
        self.uvm_files_list_lv.controls.clear()
        uvm_dir = PROJECT_ROOT_DIR / "generated_outputs" / "uvm_tests"
        if uvm_dir.exists():
            for item in sorted(uvm_dir.iterdir()):
                if item.is_file() and item.suffix in ['.sv', '.v', '.vh']:
                    uvm_control = ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=ft.Colors.BLUE_GREY_300), ft.Text(item.name, overflow=ft.TextOverflow.ELLIPSIS)], spacing=5),
                        tooltip=f"View or manage {item.name}",
                        on_click=lambda _, f=item: self._select_uvm_file(f),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                    )
                    self.uvm_files_list_lv.controls.append(uvm_control)
        if not self.uvm_files_list_lv.controls:
            self.uvm_files_list_lv.controls.append(ft.Text("No UVM files found.", italic=True, color=ft.Colors.GREY_500))
        self.uvm_files_list_lv.update()

    def _select_uvm_file(self, file_path: Path):
        self.selected_uvm_file_path = file_path
        self.log_message(f"Selected UVM file: {file_path.name}", category="INFO")

    def view_selected_uvm_file(self, e):
        if not self.selected_uvm_file_path:
            self.log_message("No UVM file selected to view.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a UVM file from the list first."), open=True))
            return
        self.view_file_dialog(self.selected_uvm_file_path)

    def generate_uvm_plan_in_uvm_tab(self, e):
        feature_desc = self.uvm_feature_desc_text.value
        if not feature_desc:
            self.log_message("Feature description is required to generate UVM verification plan.", category="WARNING")
            return
        
        cmd_args = ["gen_uvm_plan", "--feature", feature_desc,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value]
        
        self.run_orchestrator_command_threaded(
            cmd_args,
            "UVM Verification Plan Generated Successfully!",
            "UVM Plan Generation",
            on_complete_callback=self.refresh_uvm_files_list
        )

    # --- Console Tab Methods ---
    def clear_console(self, e):
        self.console_log_lv.controls.clear()
        self.log_message("Console cleared.", category="INFO")
        self.console_log_lv.update()
    
    def save_console_log(self, e):
        default_log_dir = PROJECT_ROOT_DIR / "generated_outputs" / "logs"
        default_log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_save_file_picker.save_file(
            dialog_title="Save Console Log As...",
            file_name=f"console_log_{timestamp}.txt",
            initial_directory=str(default_log_dir),
            allowed_extensions=["txt", "log"]
        )

    def _on_log_save_file_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            log_file_path = Path(e.path)
            try:
                log_content = "\n".join([control.value for control in self.console_log_lv.controls if isinstance(control, ft.Text) and control.key != 'last'])
                log_file_path.write_text(log_content, encoding='utf-8')
                self.log_message(f"Console log saved to: {log_file_path}", category="SUCCESS")
            except Exception as ex:
                self.log_message(f"Error saving console log: {ex}", category="ERROR")
                self.page.show_snack_bar(ft.SnackBar(ft.Text(f"Error saving log: {ex}"), open=True))
        else:
            self.log_message("Save log operation cancelled.", category="INFO")

    # --- Utilities Tab Methods ---
    def browse_pdf_file(self, e):
        pdf_picker = ft.FilePicker(on_result=self._on_pdf_file_picked)
        self.page.overlay.append(pdf_picker)
        self.page.update()
        pdf_picker.pick_files(
            dialog_title="Select PDF File",
            allowed_extensions=["pdf"],
            allow_multiple=False
        )

    def _on_pdf_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            self.pdf_file_text.value = e.files[0].path
            self.log_message(f"PDF file selected: {e.files[0].path}", category="INFO")
        else:
            self.pdf_file_text.value = ""
        self.pdf_file_text.update()

    def convert_pdf_to_markdown(self, e):
        pdf_file = self.pdf_file_text.value
        if not pdf_file:
            self.log_message("PDF file is required for conversion.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a PDF file first."), open=True))
            return

        cmd_args = [sys.executable, str(PROJECT_ROOT_DIR / "convert_pdfs.py"), pdf_file]
        if self.vision_enable_checkbox.value:
            cmd_args.append("--enable-vision")

        self.run_orchestrator_command_threaded(
            cmd_args,
            "PDF Converted to Markdown Successfully!",
            "PDF Conversion"
        )

    def browse_comp_spec_file(self, e):
        comp_spec_picker = ft.FilePicker(on_result=self._on_comp_spec_file_picked)
        self.page.overlay.append(comp_spec_picker)
        self.page.update()
        comp_spec_picker.pick_files(
            dialog_title="Select Specification File",
            allowed_extensions=["txt", "md", "pdf"],
            allow_multiple=False
        )

    def _on_comp_spec_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            self.comp_spec_file_text.value = e.files[0].path
            self.log_message(f"Specification file selected: {e.files[0].path}", category="INFO")
        else:
            self.comp_spec_file_text.value = ""
        self.comp_spec_file_text.update()

    def browse_comp_memmap_file(self, e):
        comp_memmap_picker = ft.FilePicker(on_result=self._on_comp_memmap_file_picked)
        self.page.overlay.append(comp_memmap_picker)
        self.page.update()
        comp_memmap_picker.pick_files(
            dialog_title="Select Memory Map File",
            allowed_extensions=["txt", "csv", "json"],
            allow_multiple=False
        )

    def _on_comp_memmap_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            self.comp_memmap_file_text.value = e.files[0].path
            self.log_message(f"Memory map file selected: {e.files[0].path}", category="INFO")
        else:
            self.comp_memmap_file_text.value = ""
        self.comp_memmap_file_text.update()

    def browse_comp_output_dir(self, e):
        comp_output_picker = ft.FilePicker(on_result=self._on_comp_output_dir_picked)
        self.page.overlay.append(comp_output_picker)
        self.page.update()
        comp_output_picker.get_directory_path(dialog_title="Select Comprehensive Output Directory")

    def _on_comp_output_dir_picked(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.comp_output_dir_text.value = e.path
            self.log_message(f"Comprehensive output directory selected: {e.path}", category="INFO")
        else:
            self.log_message("Comprehensive output directory selection cancelled.", category="INFO")
        self.comp_output_dir_text.update()

    def generate_comprehensive_tests(self, e):
        spec_file = self.comp_spec_file_text.value
        output_dir = self.comp_output_dir_text.value
        memmap_file = self.comp_memmap_file_text.value

        if not spec_file:
            self.log_message("Specification file is required for comprehensive generation.", category="WARNING")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Please select a specification file first."), open=True))
            return

        cmd_args = ["generate_comprehensive", spec_file, "--output_dir", output_dir,
                    "--openrouter-key", self.api_key_field.value,
                    "--llm-model", self.model_name_field.value, "--verbose"]
        if memmap_file:
            cmd_args.extend(["--memory_map", memmap_file])

        self.run_orchestrator_command_threaded(
            cmd_args,
            "Comprehensive Tests Generated Successfully!",
            "Comprehensive Generation"
        )

    # --- UI Building ---
    def build_setup_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("API Configuration", size=20, weight=ft.FontWeight.BOLD),
                    self.api_key_field,
                    self.model_name_field,
                    ft.Row([
                        ft.ElevatedButton("Test API Connection", icon=ft.Icons.POWER_SETTINGS_NEW, on_click=self.test_api_connection, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                        self.api_status_label,
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    ft.Divider(height=20),
                    ft.Text("Knowledge Base Management", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Populate Knowledge Base", icon=ft.Icons.LIBRARY_ADD_CHECK_ROUNDED, on_click=self.populate_kb, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                        ft.ElevatedButton("Refresh KB (Force Repopulate)", icon=ft.Icons.REFRESH_ROUNDED, on_click=self.refresh_kb, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], spacing=10),
                    self.kb_status_label,
                    ft.Divider(height=20),
                    ft.Text("Project Structure", size=16, weight=ft.FontWeight.W_600),
                    self.project_structure_display,
                ],
                spacing=15, scroll=ft.ScrollMode.ADAPTIVE,
            ),
            padding=20, expand=True, alignment=ft.alignment.top_left
        )

    def build_c_plans_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("C Verification Plan Generation", size=20, weight=ft.FontWeight.BOLD),
                    self.feature_desc_text,                    ft.Row([
                        self.spec_file_path_text, # Use Expanded for TextField
                        ft.ElevatedButton("Browse Spec File", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_spec_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END), # Align button with bottom of text field
                    ft.Row([
                        ft.ElevatedButton("Generate C Verification Plan", icon=ft.Icons.ADD_TASK_ROUNDED, on_click=self.generate_c_verification_plan, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                        ft.ElevatedButton("Generate UVM Plan (from this input)", icon=ft.Icons.ADD_TO_QUEUE_ROUNDED, on_click=self.generate_uvm_verification_plan_from_c_tab, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], spacing=10),
                    ft.Divider(height=20),
                    ft.Text("Generated C Plans", size=16, weight=ft.FontWeight.W_600),
                    ft.Container(
                        content=self.c_plans_list_lv, 
                        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), 
                        border_radius=5, 
                        padding=10, 
                        expand=True, # Make ListView container expand
                        height=200 # Fixed height or expand
                    ),
                    ft.Row([
                        ft.ElevatedButton("View Selected Plan", icon=ft.Icons.PAGEVIEW_ROUNDED, on_click=self.view_selected_c_plan, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                        ft.ElevatedButton("Export Selected to Excel", icon=ft.Icons.TABLE_CHART_ROUNDED, on_click=self.export_c_plan_to_excel, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], spacing=10),
                ],
                spacing=15, scroll=ft.ScrollMode.ADAPTIVE,
            ),
            padding=20, expand=True, alignment=ft.alignment.top_left
        )

    def build_c_tests_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("C Test Generation", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        self.c_plan_for_tests_path_text,
                        ft.ElevatedButton("Browse Plan File", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_c_plan_for_tests, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        self.c_tests_output_dir_text,
                        ft.ElevatedButton("Select Output Dir", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_c_tests_output_dir, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        self.addr_map_file_text,
                        ft.ElevatedButton("Browse Addr Map", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_addr_map_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        ft.ElevatedButton("Generate C Tests", icon=ft.Icons.ADD_TASK_ROUNDED, on_click=self.generate_c_tests, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                    ]),
                    ft.Divider(height=20),
                    ft.Text("Generated C Tests", size=16, weight=ft.FontWeight.W_600),
                    ft.Container(
                        content=self.c_tests_list_lv, 
                        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), 
                        border_radius=5, 
                        padding=10, 
                        expand=True,
                        height=200
                    ),
                    ft.Row([
                        ft.ElevatedButton("View Selected Test", icon=ft.Icons.PAGEVIEW_ROUNDED, on_click=self.view_selected_c_test, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                        ft.ElevatedButton("Regenerate Selected", icon=ft.Icons.REFRESH_ROUNDED, on_click=self.regenerate_selected_c_test, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], spacing=10),
                ],
                spacing=15, scroll=ft.ScrollMode.ADAPTIVE,
            ),
            padding=20, expand=True, alignment=ft.alignment.top_left
        )

    def build_uvm_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("UVM Generation", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("UVM Plan Generation", size=16, weight=ft.FontWeight.W_600),
                    self.uvm_feature_desc_text,
                    ft.Row([
                        ft.ElevatedButton("Generate UVM Plan", icon=ft.Icons.ADD_TASK_ROUNDED, on_click=self.generate_uvm_plan_in_uvm_tab, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                    ]),
                    ft.Divider(height=20),
                    ft.Text("UVM Test Generation", size=16, weight=ft.FontWeight.W_600),
                    ft.Row([
                        self.uvm_plan_file_text,
                        ft.ElevatedButton("Browse UVM Plan", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_uvm_plan_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        self.uvm_output_dir_text,
                        ft.ElevatedButton("Select Output Dir", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_uvm_output_dir, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    self.coverage_enable_checkbox,
                    ft.Row([
                        ft.ElevatedButton("Generate UVM Tests", icon=ft.Icons.ADD_TASK_ROUNDED, on_click=self.generate_uvm_tests, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                    ]),
                    ft.Divider(height=20),
                    ft.Text("Generated UVM Files", size=16, weight=ft.FontWeight.W_600),
                    ft.Container(
                        content=self.uvm_files_list_lv, 
                        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), 
                        border_radius=5, 
                        padding=10, 
                        expand=True,
                        height=200
                    ),
                    ft.Row([
                        ft.ElevatedButton("View Selected File", icon=ft.Icons.PAGEVIEW_ROUNDED, on_click=self.view_selected_uvm_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], spacing=10),
                ],
                spacing=15, scroll=ft.ScrollMode.ADAPTIVE,
            ),            padding=20, expand=True, alignment=ft.alignment.top_left
        )

    def build_utilities_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Utilities & Tools", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("PDF Processing", size=16, weight=ft.FontWeight.W_600),
                    ft.Row([
                        self.pdf_file_text,
                        ft.ElevatedButton("Browse PDF", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_pdf_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    self.vision_enable_checkbox,
                    ft.Row([
                        ft.ElevatedButton("Convert PDF to Markdown", icon=ft.Icons.TRANSFORM_ROUNDED, on_click=self.convert_pdf_to_markdown, style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                    ]),
                    ft.Divider(height=20),
                    ft.Text("Comprehensive Generation", size=16, weight=ft.FontWeight.W_600),
                    ft.Row([
                        self.comp_spec_file_text,
                        ft.ElevatedButton("Browse Spec File", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_comp_spec_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        self.comp_memmap_file_text,
                        ft.ElevatedButton("Browse Memmap File", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_comp_memmap_file, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        self.comp_output_dir_text,
                        ft.ElevatedButton("Select Output Dir", icon=ft.Icons.FOLDER_OPEN, on_click=self.browse_comp_output_dir, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))),
                    ], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Row([
                        ft.ElevatedButton("Generate Comprehensive Tests", icon=ft.Icons.RUN_CIRCLE_ROUNDED, on_click=self.generate_comprehensive_tests, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_100, shape=ft.RoundedRectangleBorder(radius=5))),
                    ]),
                ],
                spacing=15, scroll=ft.ScrollMode.ADAPTIVE,
            ),
            padding=20, expand=True, alignment=ft.alignment.top_left
        )

    def build_console_tab_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Text("Console Output", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.auto_scroll_checkbox,
                            ft.IconButton(ft.Icons.DELETE_SWEEP_ROUNDED, tooltip="Clear Console", on_click=self.clear_console),
                            ft.IconButton(ft.Icons.SAVE_ALT_ROUNDED, tooltip="Save Log", on_click=self.save_console_log), # Disabled for now
                        ], alignment=ft.MainAxisAlignment.END)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(
                        content=self.console_log_lv, 
                        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), 
                        border_radius=5, 
                        padding=5, 
                        expand=True # Make console expand
                    ),
                ],
                spacing=10, expand=True        ),
            padding=ft.padding.only(left=20, right=20, top=10, bottom=10), expand=True
        )

    def build_ui(self):
        self.tabs_control = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Setup & Config", icon=ft.Icons.SETTINGS_APPLICATIONS_ROUNDED, content=self.build_setup_tab_content()),
                ft.Tab(text="C Plans", icon=ft.Icons.POST_ADD_ROUNDED, content=self.build_c_plans_tab_content()),
                ft.Tab(text="C Tests", icon=ft.Icons.TEXT_SNIPPET_ROUNDED, content=self.build_c_tests_tab_content()),
                ft.Tab(text="UVM", icon=ft.Icons.DEVELOPER_BOARD_ROUNDED, content=self.build_uvm_tab_content()),
                ft.Tab(text="Utilities", icon=ft.Icons.CONSTRUCTION_ROUNDED, content=self.build_utilities_tab_content()),
                ft.Tab(text="Console", icon=ft.Icons.TERMINAL_ROUNDED, content=self.build_console_tab_content()),
            ],
            expand=True, # Tabs control itself should expand
        )
        self.page.add(self.tabs_control)
        self.page.update()

def main(page: ft.Page):
    # page.window_width = 1200 # Optional: set initial window size
    # page.window_height = 800
    page.window_maximizable = True
    page.window_resizable = True
    
    # Configure custom font if available (example)
    # page.fonts = {
    #     "RobotoMono": "RobotoMono-VariableFont_wght.ttf" 
    # }
    # page.theme = ft.Theme(font_family="RobotoMono")


    app_instance = ModernApp(page)
    # You can call methods on app_instance here if needed before page.update() or page.go()

if __name__ == "__main__":
    ft.app(target=main) #, assets_dir="assets") # If you have assets like fonts
