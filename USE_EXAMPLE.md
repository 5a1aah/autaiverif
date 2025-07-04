    python convert_pdfs.py "knowledge_base_src\specs\CVA6_Testharness.pdf" --vision 

    python main_orchestrator.py populate_kb           


    python main_orchestrator.py gen_plan --feature "CLINT registers access"


    python main_orchestrator.py plan_to_excel --plan_file .\generated_outputs\verification_plans\verif_plan_CLINT_registers_access.md --excel_file generated_outputs/excel_reports/report_clint_registers_access.xlsx


    python main_orchestrator.py gen_tests --plan_file generated_outputs\verification_plans\verif_plan_CLINT_registers_access.md



## UVM Test Generation

    python main_orchestrator.py gen_uvm_plan --feature "CLINT timer interrupt"


    python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_CLINT_timer_interrupt.md"
    

    python main_orchestrator.py gen_uvm_tests "generated_outputs\uvm_verification_plans\uvm_verif_plan_CLINT_timer_interrupt.md" --coverage_enable --output "generated_outputs\clint_tests_with_coverage"