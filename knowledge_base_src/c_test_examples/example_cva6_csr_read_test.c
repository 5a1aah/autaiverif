/**
 * @file example_cva6_csr_read_test.c
 * @brief Example C test for reading a CVA6 CSR (mvendorid).
 *
 * This test demonstrates basic interaction with the CVA6 HAL to read a CSR
 * and assert its expected properties (though for mvendorid, the exact value
 * might vary, so we mostly check if it's non-zero or a known range if applicable).
 */

 #include <stdio.h> // For VERIF_LOG if it uses printf-like functions
 #include <stdint.h>
 #include "cva6_hal.h" // Assumed HAL header for CVA6 CSR functions
 // #include "test_framework.h" // Assumed test framework header
 
 // --- Test Framework Macros (Example Definitions - use your actual ones) ---
 // These would typically be in "test_framework.h"
 #ifndef VERIF_LOG
 #define VERIF_LOG(level, module, test_id_str, format, ...) \
     printf("[%s] %s - %s: " format "\n", level, module, test_id_str, ##__VA_ARGS__)
 #endif
 
 #ifndef ASSERT_NOT_EQUAL // Example, could be ASSERT_TRUE, ASSERT_GREATER_THAN etc.
 #define ASSERT_NOT_EQUAL(actual, unexpected, message) \
     do { \
         if ((actual) == (unexpected)) { \
             VERIF_LOG("ERROR", "CSR_Test", current_test_id_global, "Assertion Failed: %s. Actual (%llx) == Unexpected (%llx)", message, (unsigned long long)actual, (unsigned long long)unexpected); \
             return 1; /* Test failed */ \
         } else { \
             VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Assertion Passed: %s. Actual (%llx) != Unexpected (%llx)", message, (unsigned long long)actual, (unsigned long long)unexpected); \
         } \
     } while (0)
 #endif
 
 // CSR Address Definitions (from a hypothetical register map header or standard defines)
 #define CSR_MVENDORID   0xF11
 #define CSR_MHARTID     0xF14
 
 // Global for test ID in macros - a bit of a hack for simple examples, better test frameworks handle this
 static const char* current_test_id_global = "CVA6_CSR_READ_001";
 
 /**
  * @brief Test: Read mvendorid CSR.
  *
  * Description: This test reads the Machine Vendor ID CSR (mvendorid).
  * It verifies that a value is read, and typically, one might check if it's non-zero
  * or matches an expected known vendor ID if applicable for the specific CVA6 instance.
  *
  * Stimulus:
  * 1. Call HAL function to read CSR mvendorid.
  *
  * Expected Outcome:
  * 1. The read value should be non-zero (as a generic check).
  * (A more specific test would check against the OpenHW Group's vendor ID if known and fixed).
  */
 int test_CVA6_CSR_READ_001(void) {
     uint64_t mvendorid_val;
     uint64_t mhartid_val; // Also read hartid for a simple comparison
 
     current_test_id_global = "CVA6_CSR_READ_001"; // Set current test ID for logging
 
     VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Starting test: Read mvendorid CSR.");
 
     // 1. Read mvendorid CSR
     mvendorid_val = hal_cva6_read_csr(CSR_MVENDORID);
     VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Read mvendorid = 0x%016llx", (unsigned long long)mvendorid_val);
 
     // 2. Basic Assertion: Check if mvendorid is not zero (a very generic check)
     // In a real scenario, you might have an expected ID, e.g., OpenHW Group's ID.
     ASSERT_NOT_EQUAL(mvendorid_val, 0x0ULL, "mvendorid should be non-zero");
 
     // Example of reading another CSR for context
     mhartid_val = hal_cva6_read_csr(CSR_MHARTID);
     VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Read mhartid = 0x%016llx", (unsigned long long)mhartid_val);
     // mhartid is usually 0 for a uniprocessor system or the first core.
     // No specific assertion here, just showing another read.
 
     VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Test completed successfully.");
     return 0; // Test passed
 }
 
 /*
 // You could add more test functions here following the same pattern
 int test_CVA6_CSR_WRITE_READ_001(void) {
     current_test_id_global = "CVA6_CSR_WRITE_READ_001";
     VERIF_LOG("INFO", "CSR_Test", current_test_id_global, "Starting test: Write and Read mscratch CSR.");
     // ... implementation for writing and reading mscratch ...
     // uint64_t test_val = 0xABCDEF0123456789ULL;
     // hal_cva6_write_csr(0x340, test_val); // CSR_MSCRATCH = 0x340
     // uint64_t read_val = hal_cva6_read_csr(0x340);
     // ASSERT_EQUAL(read_val, test_val, "mscratch readback value mismatch");
     return 0;
 }
 */
 
 // Optional main for standalone testing of this example file
 #ifdef CVA6_CSR_EXAMPLE_STANDALONE
 int main() {
     int result;
     printf("--- Running CVA6 CSR Read Example Test ---\n");
     result = test_CVA6_CSR_READ_001();
     if (result == 0) {
         printf("--- TEST PASSED ---\n");
     } else {
         printf("--- TEST FAILED ---\n");
     }
     return result;
 }
 #endif // CVA6_CSR_EXAMPLE_STANDALONE