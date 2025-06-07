/**
 * @file uvm_test.sv
 * @brief Reference UVM test implementation for CVA6 ASIC verification
 * 
 * This file contains a complete UVM test example that demonstrates:
 * - Proper UVM test class structure and inheritance
 * - Configuration and build phases
 * - Sequence execution and objection handling
 * - Coverage collection and self-checking
 * - Error handling and timeout mechanisms
 * - Integration with project_sequences.sv
 */

`ifndef UVM_TEST_SV
`define UVM_TEST_SV

// Include UVM macros and packages
`include "uvm_macros.svh"
import uvm_pkg::*;

// Import project-specific packages
// import cva6_pkg::*;
// import project_sequences_pkg::*;

class cva6_base_test extends uvm_test;
    `uvm_component_utils(cva6_base_test)

    // Environment instance
    // cva6_env env;

    // Configuration objects
    // cva6_env_config env_cfg;
    // axi_agent_config axi_cfg;

    // Test control variables
    protected bit test_passed = 1;
    protected int timeout_cycles = 10000;
    protected int error_count = 0;

    // Coverage groups for functional coverage
    covergroup test_coverage with function sample();
        option.per_instance = 1;
        option.name = "test_coverage";
        
        // Add coverage points specific to test requirements
        test_phase_cp: coverpoint get_test_phase() {
            bins reset_phase = {RESET_PHASE};
            bins config_phase = {CONFIG_PHASE};
            bins stimulus_phase = {STIMULUS_PHASE};
            bins check_phase = {CHECK_PHASE};
        }
    endgroup

    // Test phase enumeration
    typedef enum {
        RESET_PHASE,
        CONFIG_PHASE, 
        STIMULUS_PHASE,
        CHECK_PHASE
    } test_phase_e;

    protected test_phase_e current_phase = RESET_PHASE;

    function new(string name = "cva6_base_test", uvm_component parent = null);
        super.new(name, parent);
        test_coverage = new();
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        `uvm_info(get_type_name(), "Starting build_phase", UVM_LOW)
        
        // Create and configure environment
        // env_cfg = cva6_env_config::type_id::create("env_cfg");
        // configure_environment();
        
        // Create environment
        // env = cva6_env::type_id::create("env", this);
        
        `uvm_info(get_type_name(), "build_phase completed", UVM_LOW)
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        `uvm_info(get_type_name(), "connect_phase completed", UVM_LOW)
    endfunction

    virtual function void end_of_elaboration_phase(uvm_phase phase);
        super.end_of_elaboration_phase(phase);
        `uvm_info(get_type_name(), "end_of_elaboration_phase completed", UVM_LOW)
        print_test_info();
    endfunction

    virtual task run_phase(uvm_phase phase);
        `uvm_info(get_type_name(), "Starting run_phase", UVM_LOW)
        
        // Raise objection to keep test running
        phase.raise_objection(this, "Starting main test sequence");
        
        fork
            // Main test execution
            execute_test_sequence();
            
            // Timeout watchdog
            timeout_watchdog();
        join_any
        
        // Drop objection to end test
        phase.drop_objection(this, "Test sequence completed");
        
        `uvm_info(get_type_name(), "run_phase completed", UVM_LOW)
    endtask

    virtual task execute_test_sequence();
        `uvm_info(get_type_name(), "Executing main test sequence", UVM_MEDIUM)
        
        // Phase 1: Reset and initialization
        current_phase = RESET_PHASE;
        test_coverage.sample();
        execute_reset_phase();
        
        // Phase 2: Configuration
        current_phase = CONFIG_PHASE;
        test_coverage.sample();
        execute_config_phase();
        
        // Phase 3: Stimulus generation
        current_phase = STIMULUS_PHASE;
        test_coverage.sample();
        execute_stimulus_phase();
        
        // Phase 4: Results checking
        current_phase = CHECK_PHASE;
        test_coverage.sample();
        execute_check_phase();
        
        `uvm_info(get_type_name(), "Main test sequence completed", UVM_MEDIUM)
    endtask

    virtual task execute_reset_phase();
        `uvm_info(get_type_name(), "Executing reset phase", UVM_MEDIUM)
        
        // Wait for reset deassertion
        // wait(vif.reset_n === 1'b1);
        
        // Additional reset timing
        #100ns;
        
        `uvm_info(get_type_name(), "Reset phase completed", UVM_MEDIUM)
    endtask

    virtual task execute_config_phase();
        `uvm_info(get_type_name(), "Executing configuration phase", UVM_MEDIUM)
        
        // Example: Configure CSR registers using csr_access_sequence
        // csr_access_sequence csr_seq;
        // csr_seq = csr_access_sequence::type_id::create("csr_seq");
        // csr_seq.start(env.csr_agent.sequencer);
        
        `uvm_info(get_type_name(), "Configuration phase completed", UVM_MEDIUM)
    endtask

    virtual task execute_stimulus_phase();
        `uvm_info(get_type_name(), "Executing stimulus phase", UVM_MEDIUM)
        
        // Example: Execute AXI transactions using axi_read_sequence and axi_write_sequence
        // axi_read_sequence read_seq;
        // axi_write_sequence write_seq;
        
        // read_seq = axi_read_sequence::type_id::create("read_seq");
        // read_seq.address = 32'h1000_0000;
        // read_seq.num_reads = 10;
        // read_seq.start(env.axi_agent.sequencer);
        
        // write_seq = axi_write_sequence::type_id::create("write_seq");
        // write_seq.address = 32'h1000_0100;
        // write_seq.data = 32'hDEAD_BEEF;
        // write_seq.num_writes = 5;
        // write_seq.start(env.axi_agent.sequencer);
        
        // Example: Execute interrupt sequence
        // interrupt_sequence int_seq;
        // int_seq = interrupt_sequence::type_id::create("int_seq");
        // int_seq.start(env.interrupt_agent.sequencer);
        
        `uvm_info(get_type_name(), "Stimulus phase completed", UVM_MEDIUM)
    endtask

    virtual task execute_check_phase();
        `uvm_info(get_type_name(), "Executing check phase", UVM_MEDIUM)
        
        // Wait for all transactions to complete
        #1000ns;
        
        // Check scoreboard results
        // check_scoreboard_results();
        
        // Verify coverage goals
        check_coverage_goals();
        
        `uvm_info(get_type_name(), "Check phase completed", UVM_MEDIUM)
    endtask

    virtual task timeout_watchdog();
        `uvm_info(get_type_name(), $sformatf("Starting timeout watchdog (%0d cycles)", timeout_cycles), UVM_LOW)
        
        repeat(timeout_cycles) begin
            // @(posedge vif.clk);
            #10ns; // Simplified for example
        end
        
        `uvm_error(get_type_name(), $sformatf("Test timeout after %0d cycles", timeout_cycles))
        test_passed = 0;
    endtask

    virtual function void check_coverage_goals();
        real coverage_percentage;
        
        coverage_percentage = test_coverage.get_coverage();
        `uvm_info(get_type_name(), $sformatf("Test coverage: %0.2f%%", coverage_percentage), UVM_MEDIUM)
        
        if (coverage_percentage < 80.0) begin
            `uvm_warning(get_type_name(), $sformatf("Coverage goal not met: %0.2f%% < 80%%", coverage_percentage))
        end
    endfunction

    virtual function void report_phase(uvm_phase phase);
        super.report_phase(phase);
        
        `uvm_info(get_type_name(), "=== TEST SUMMARY ===", UVM_LOW)
        `uvm_info(get_type_name(), $sformatf("Test Status: %s", test_passed ? "PASSED" : "FAILED"), UVM_LOW)
        `uvm_info(get_type_name(), $sformatf("Error Count: %0d", error_count), UVM_LOW)
        
        // Print coverage summary
        `uvm_info(get_type_name(), $sformatf("Functional Coverage: %0.2f%%", test_coverage.get_coverage()), UVM_LOW)
        
        if (!test_passed) begin
            `uvm_error(get_type_name(), "TEST FAILED - Check log for details")
        end else begin
            `uvm_info(get_type_name(), "TEST PASSED", UVM_LOW)
        end
        
        `uvm_info(get_type_name(), "=== END TEST SUMMARY ===", UVM_LOW)
    endfunction

    // Helper functions
    virtual function void print_test_info();
        `uvm_info(get_type_name(), "=== TEST INFORMATION ===", UVM_LOW)
        `uvm_info(get_type_name(), $sformatf("Test Name: %s", get_name()), UVM_LOW)
        `uvm_info(get_type_name(), $sformatf("Test Type: %s", get_type_name()), UVM_LOW)
        `uvm_info(get_type_name(), $sformatf("Timeout: %0d cycles", timeout_cycles), UVM_LOW)
        `uvm_info(get_type_name(), "=== END TEST INFORMATION ===", UVM_LOW)
    endfunction

    virtual function test_phase_e get_test_phase();
        return current_phase;
    endfunction

    virtual function void configure_environment();
        // Override in derived tests to configure environment
        `uvm_info(get_type_name(), "Base environment configuration", UVM_MEDIUM)
    endfunction

    // Error handling utilities
    virtual function void increment_error_count(string message = "");
        error_count++;
        test_passed = 0;
        if (message != "") begin
            `uvm_error(get_type_name(), message)
        end
    endfunction

    virtual function bit check_condition(bit condition, string message);
        if (!condition) begin
            increment_error_count(message);
            return 0;
        end
        return 1;
    endfunction

endclass : cva6_base_test

// Example of a specific test derived from base test
class cva6_axi_basic_test extends cva6_base_test;
    `uvm_component_utils(cva6_axi_basic_test)

    function new(string name = "cva6_axi_basic_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual function void configure_environment();
        super.configure_environment();
        
        // Configure AXI-specific settings
        // env_cfg.axi_cfg.enable_axi_checks = 1;
        // env_cfg.axi_cfg.max_outstanding_transactions = 4;
        
        `uvm_info(get_type_name(), "AXI basic test environment configured", UVM_MEDIUM)
    endfunction

    virtual task execute_stimulus_phase();
        `uvm_info(get_type_name(), "Executing AXI-specific stimulus", UVM_MEDIUM)
        
        // Execute AXI-specific sequences using project_sequences.sv
        // axi_read_sequence read_seq;
        // axi_write_sequence write_seq;
        
        // Basic read test
        // read_seq = axi_read_sequence::type_id::create("basic_read_seq");
        // assert(read_seq.randomize() with {
        //     num_reads inside {[1:10]};
        //     address inside {[32'h1000_0000:32'h1000_FFFF]};
        // });
        // read_seq.start(env.axi_agent.sequencer);
        
        // Basic write test  
        // write_seq = axi_write_sequence::type_id::create("basic_write_seq");
        // assert(write_seq.randomize() with {
        //     num_writes inside {[1:10]};
        //     address inside {[32'h1000_0000:32'h1000_FFFF]};
        // });
        // write_seq.start(env.axi_agent.sequencer);
        
        super.execute_stimulus_phase();
    endtask

endclass : cva6_axi_basic_test

// Example of an interrupt-focused test
class cva6_interrupt_test extends cva6_base_test;
    `uvm_component_utils(cva6_interrupt_test)

    function new(string name = "cva6_interrupt_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction

    virtual task execute_stimulus_phase();
        `uvm_info(get_type_name(), "Executing interrupt-specific stimulus", UVM_MEDIUM)
        
        // Execute interrupt sequences using project_sequences.sv
        // interrupt_sequence int_seq;
        // int_seq = interrupt_sequence::type_id::create("int_seq");
        // assert(int_seq.randomize() with {
        //     interrupt_type inside {SOFTWARE_INT, TIMER_INT, EXTERNAL_INT};
        // });
        // int_seq.start(env.interrupt_agent.sequencer);
        
        super.execute_stimulus_phase();
    endtask

    virtual task execute_check_phase();
        super.execute_check_phase();
        
        // Additional interrupt-specific checks
        // verify_interrupt_handling();
    endtask

endclass : cva6_interrupt_test

`endif // UVM_TEST_SV
