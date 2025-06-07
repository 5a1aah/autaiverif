/**
 * @file project_sequences.sv
 * @brief UVM sequence library for CVA6 ASIC verification
 * 
 * This file contains reusable UVM sequences that can be used as reference
 * for generating UVM test cases for various CVA6 ASIC features.
 */

// Base sequence class for CVA6 verification
class cva6_base_sequence extends uvm_sequence #(cva6_transaction);
    `uvm_object_utils(cva6_base_sequence)
    
    function new(string name = "cva6_base_sequence");
        super.new(name);
    endfunction
    
    virtual task pre_body();
        uvm_phase phase;
        `ifdef UVM_VERSION_1_2
            phase = get_starting_phase();
        `else
            phase = starting_phase;
        `endif
        if (phase != null) begin
            phase.raise_objection(this, get_type_name());
            `uvm_info(get_type_name(), "raise objection", UVM_MEDIUM)
        end
    endtask
    
    virtual task post_body();
        uvm_phase phase;
        `ifdef UVM_VERSION_1_2
            phase = get_starting_phase();
        `else
            phase = starting_phase;
        `endif
        if (phase != null) begin
            phase.drop_objection(this, get_type_name());
            `uvm_info(get_type_name(), "drop objection", UVM_MEDIUM)
        end
    endtask
endclass

// AXI read sequence for memory-mapped register access
class axi_read_sequence extends cva6_base_sequence;
    `uvm_object_utils(axi_read_sequence)
    
    rand bit [63:0] address;
    rand int num_reads = 1;
    
    constraint addr_c {
        address inside {[32'h1000_0000:32'h1FFF_FFFF]}; // CVA6 peripheral space
    }
    
    constraint num_reads_c {
        num_reads inside {[1:10]};
    }
    
    function new(string name = "axi_read_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        for (int i = 0; i < num_reads; i++) begin
            req = cva6_transaction::type_id::create("req");
            start_item(req);
            assert(req.randomize() with {
                req.cmd == READ;
                req.addr == local::address + (i * 4);
                req.data == 0;
            });
            finish_item(req);
            get_response(rsp);
            `uvm_info(get_type_name(), 
                     $sformatf("AXI Read: addr=0x%0h, data=0x%0h", req.addr, rsp.data), 
                     UVM_MEDIUM)
        end
    endtask
endclass

// AXI write sequence for memory-mapped register configuration
class axi_write_sequence extends cva6_base_sequence;
    `uvm_object_utils(axi_write_sequence)
    
    rand bit [63:0] address;
    rand bit [63:0] data;
    rand int num_writes = 1;
    
    constraint addr_c {
        address inside {[32'h1000_0000:32'h1FFF_FFFF]}; // CVA6 peripheral space
    }
    
    constraint num_writes_c {
        num_writes inside {[1:10]};
    }
    
    function new(string name = "axi_write_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        for (int i = 0; i < num_writes; i++) begin
            req = cva6_transaction::type_id::create("req");
            start_item(req);
            assert(req.randomize() with {
                req.cmd == WRITE;
                req.addr == local::address + (i * 4);
                req.data == local::data + i;
            });
            finish_item(req);
            get_response(rsp);
            `uvm_info(get_type_name(), 
                     $sformatf("AXI Write: addr=0x%0h, data=0x%0h", req.addr, req.data), 
                     UVM_MEDIUM)
        end
    endtask
endclass

// CSR (Control and Status Register) access sequence
class csr_access_sequence extends cva6_base_sequence;
    `uvm_object_utils(csr_access_sequence)
    
    typedef enum {
        CSR_MVENDORID = 12'hF11,
        CSR_MHARTID   = 12'hF14,
        CSR_MSTATUS   = 12'h300,
        CSR_MSCRATCH  = 12'h340,
        CSR_MEPC      = 12'h341,
        CSR_MCAUSE    = 12'h342
    } csr_addr_e;
    
    rand csr_addr_e csr_addr;
    rand bit [63:0] write_data;
    rand bit do_write;
    
    constraint write_c {
        do_write dist {0 := 70, 1 := 30}; // 70% reads, 30% writes
    }
    
    function new(string name = "csr_access_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        req = cva6_transaction::type_id::create("req");
        start_item(req);
        
        if (do_write) begin
            assert(req.randomize() with {
                req.cmd == CSR_WRITE;
                req.csr_addr == local::csr_addr;
                req.data == local::write_data;
            });
        end else begin
            assert(req.randomize() with {
                req.cmd == CSR_READ;
                req.csr_addr == local::csr_addr;
            });
        end
        
        finish_item(req);
        get_response(rsp);
        
        `uvm_info(get_type_name(), 
                 $sformatf("CSR %s: addr=0x%0h, data=0x%0h", 
                          do_write ? "Write" : "Read", csr_addr, 
                          do_write ? req.data : rsp.data), 
                 UVM_MEDIUM)
    endtask
endclass

// Interrupt handling sequence
class interrupt_sequence extends cva6_base_sequence;
    `uvm_object_utils(interrupt_sequence)
    
    typedef enum {
        SOFTWARE_INTERRUPT = 0,
        TIMER_INTERRUPT    = 1,
        EXTERNAL_INTERRUPT = 2
    } interrupt_type_e;
    
    rand interrupt_type_e int_type;
    rand int interrupt_duration;
    
    constraint duration_c {
        interrupt_duration inside {[10:100]};
    }
    
    function new(string name = "interrupt_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        req = cva6_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
            req.cmd == INTERRUPT;
            req.int_type == local::int_type;
            req.duration == local::interrupt_duration;
        });
        finish_item(req);
        
        `uvm_info(get_type_name(), 
                 $sformatf("Interrupt triggered: type=%0d, duration=%0d", 
                          int_type, interrupt_duration), 
                 UVM_MEDIUM)
        
        // Wait for interrupt duration
        #(interrupt_duration * 1ns);
        
        // Clear interrupt
        req = cva6_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
            req.cmd == CLEAR_INTERRUPT;
            req.int_type == local::int_type;
        });
        finish_item(req);
        
        `uvm_info(get_type_name(), 
                 $sformatf("Interrupt cleared: type=%0d", int_type), 
                 UVM_MEDIUM)
    endtask
endclass

// Pipeline stress sequence for testing instruction execution
class pipeline_stress_sequence extends cva6_base_sequence;
    `uvm_object_utils(pipeline_stress_sequence)
    
    rand int num_instructions;
    rand bit use_branch_instructions;
    rand bit use_memory_instructions;
    
    constraint num_instr_c {
        num_instructions inside {[50:200]};
    }
    
    function new(string name = "pipeline_stress_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        for (int i = 0; i < num_instructions; i++) begin
            req = cva6_transaction::type_id::create("req");
            start_item(req);
            
            if (use_branch_instructions && (i % 10 == 0)) begin
                assert(req.randomize() with {
                    req.cmd == BRANCH_INSTR;
                    req.addr inside {[32'h8000_0000:32'h8FFF_FFFF]}; // Code space
                });
            end else if (use_memory_instructions && (i % 5 == 0)) begin
                assert(req.randomize() with {
                    req.cmd inside {LOAD_INSTR, STORE_INSTR};
                    req.addr inside {[32'h1000_0000:32'h1FFF_FFFF]}; // Data space
                });
            end else begin
                assert(req.randomize() with {
                    req.cmd == ALU_INSTR;
                });
            end
            
            finish_item(req);
            get_response(rsp);
        end
        
        `uvm_info(get_type_name(), 
                 $sformatf("Pipeline stress completed: %0d instructions", num_instructions), 
                 UVM_HIGH)
    endtask
endclass

// Cache coherency sequence for testing cache behavior
class cache_coherency_sequence extends cva6_base_sequence;
    `uvm_object_utils(cache_coherency_sequence)
    
    rand bit [63:0] cache_line_addr;
    rand int num_accesses;
    
    constraint cache_addr_c {
        cache_line_addr[5:0] == 0; // Align to 64-byte cache line
        cache_line_addr inside {[32'h1000_0000:32'h1FFF_FFFF]};
    }
    
    constraint num_accesses_c {
        num_accesses inside {[10:50]};
    }
    
    function new(string name = "cache_coherency_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        // Generate mixed read/write accesses to same cache line
        for (int i = 0; i < num_accesses; i++) begin
            req = cva6_transaction::type_id::create("req");
            start_item(req);
            
            assert(req.randomize() with {
                req.cmd dist {READ := 60, WRITE := 40};
                req.addr inside {[cache_line_addr:cache_line_addr+63]};
                if (req.cmd == WRITE) {
                    req.data == $random;
                }
            });
            
            finish_item(req);
            get_response(rsp);
            
            // Add small delay between accesses
            #($urandom_range(1,5) * 1ns);
        end
        
        `uvm_info(get_type_name(), 
                 $sformatf("Cache coherency test completed: %0d accesses to 0x%0h", 
                          num_accesses, cache_line_addr), 
                 UVM_HIGH)
    endtask
endclass

// Virtual memory sequence for testing MMU functionality
class virtual_memory_sequence extends cva6_base_sequence;
    `uvm_object_utils(virtual_memory_sequence)
    
    rand bit [63:0] virtual_addr;
    rand bit enable_translation;
    rand bit cause_page_fault;
    
    constraint vaddr_c {
        virtual_addr[63:39] == 0; // Stay within Sv39 virtual address space
    }
    
    constraint fault_c {
        cause_page_fault dist {0 := 90, 1 := 10}; // 10% chance of page fault
    }
    
    function new(string name = "virtual_memory_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        cva6_transaction req;
        
        // Enable/disable translation
        req = cva6_transaction::type_id::create("req");
        start_item(req);
        assert(req.randomize() with {
            req.cmd == CONFIG_MMU;
            req.enable_translation == local::enable_translation;
        });
        finish_item(req);
        
        if (enable_translation) begin
            // Perform virtual memory access
            req = cva6_transaction::type_id::create("req");
            start_item(req);
            assert(req.randomize() with {
                req.cmd == VIRTUAL_ACCESS;
                req.addr == local::virtual_addr;
                req.expect_fault == local::cause_page_fault;
            });
            finish_item(req);
            get_response(rsp);
            
            `uvm_info(get_type_name(), 
                     $sformatf("Virtual access: addr=0x%0h, fault_expected=%0b, fault_occurred=%0b", 
                              virtual_addr, cause_page_fault, rsp.fault_occurred), 
                     UVM_MEDIUM)
        end
    endtask
endclass


//----------------------------------------------------------------------
// AXI Base Sequence
//----------------------------------------------------------------------
class axi_base_seq extends uvm_sequence#(axi_item);
  function new(string name = "axi_base_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_base_seq)
  `uvm_declare_p_sequencer(axi_sequencer) // Optional, for direct sequencer access
endclass : axi_base_seq

//----------------------------------------------------------------------
// Single Write Sequence
//----------------------------------------------------------------------
class axi_single_write_seq extends axi_base_seq;
  rand bit [31:0] start_addr;
  rand bit [31:0] write_data;

  function new(string name = "axi_single_write_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_single_write_seq)

  virtual task body();
    req = axi_item::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      kind == AXI_WRITE;
      addr == start_addr;
      wdata == write_data;
    });
    finish_item(req);
  endtask : body
endclass : axi_single_write_seq

//----------------------------------------------------------------------
// Single Read Sequence
//----------------------------------------------------------------------
class axi_single_read_seq extends axi_base_seq;
  rand bit [31:0] start_addr;

  function new(string name = "axi_single_read_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_single_read_seq)

  virtual task body();
    req = axi_item::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      kind == AXI_READ;
      addr == start_addr;
    });
    finish_item(req);
    get_response(rsp);
    // Optional: Print the read data
    `uvm_info(get_type_name(), $sformatf("Read data: 0x%h from address 0x%h", rsp.rdata, rsp.addr), UVM_MEDIUM)
  endtask : body
endclass : axi_single_read_seq

//----------------------------------------------------------------------
// Burst Write Sequence
//----------------------------------------------------------------------
class axi_burst_write_seq extends axi_base_seq;
  rand bit [31:0] start_addr;
  rand int unsigned num_trans = 4; // Number of transfers in the burst

  function new(string name = "axi_burst_write_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_burst_write_seq)

  virtual task body();
    foreach (i in [0:num_trans-1]) begin
      req = axi_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        kind == AXI_WRITE;
        addr == start_addr + i * 4; // Assuming 32-bit alignment
      });
      finish_item(req);
    end
  endtask : body
endclass : axi_burst_write_seq

//----------------------------------------------------------------------
// Burst Read Sequence
//----------------------------------------------------------------------
class axi_burst_read_seq extends axi_base_seq;
  rand bit [31:0] start_addr;
  rand int unsigned num_trans = 4; // Number of transfers in the burst

  function new(string name = "axi_burst_read_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_burst_read_seq)

  virtual task body();
    foreach (i in [0:num_trans-1]) begin
      req = axi_item::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        kind == AXI_READ;
        addr == start_addr + i * 4; // Assuming 32-bit alignment
      });
      finish_item(req);
      get_response(rsp);
      `uvm_info(get_type_name(), $sformatf("Read data: 0x%h from address 0x%h", rsp.rdata, rsp.addr), UVM_MEDIUM)
    end
  endtask : body
endclass : axi_burst_read_seq

//----------------------------------------------------------------------
// Mixed Read/Write Sequence
//----------------------------------------------------------------------
class axi_mixed_read_write_seq extends axi_base_seq;
  rand int unsigned num_repeats = 5;

  function new(string name = "axi_mixed_read_write_seq");
    super.new(name);
  endfunction

  `uvm_object_utils(axi_mixed_read_write_seq)

  virtual task body();
    repeat (num_repeats) begin
      axi_single_write_seq write_seq = axi_single_write_seq::type_id::create("write_seq");
      axi_single_read_seq  read_seq  = axi_single_read_seq::type_id::create("read_seq");

      assert(write_seq.randomize());
      write_seq.start(m_sequencer);

      assert(read_seq.randomize() with { start_addr == write_seq.start_addr; });
      read_seq.start(m_sequencer);
    end
  endtask : body
endclass : axi_mixed_read_write_seq
