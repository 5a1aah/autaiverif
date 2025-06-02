 #include <stdint.h> // For uint32_t, uint64_t etc.
 // #include "my_hal.h"       // Assume your HAL functions are here
 // #include "my_test_framework.h" // Assume your test macros are here
 
 // --- Hypothetical HAL Function (would be in my_hal.h) ---
 // uint32_t hal_read_register(uint32_t register_address);
 
 // --- Hypothetical Test Framework Macros (would be in my_test_framework.h) ---
 #ifndef VERIF_LOG
 #define VERIF_LOG(level_str, test_id_str, format_str, ...) \
     printf("[%s] %s: " format_str "\n", level_str, test_id_str, ##__VA_ARGS__)
 #endif
 
 #ifndef ASSERT_EQUAL
 #define ASSERT_EQUAL(actual, expected, error_message_str) \
     do { \
         if ((actual) != (expected)) { \
             VERIF_LOG("ERROR", current_test_id, "%s - Expected: 0x%x, Got: 0xx", \
                       error_message_str, (unsigned int)expected, (unsigned int)actual); \
             return 1; /* Test failed */ \
         } \
     } while (0)
 #endif
 
 // --- Hypothetical Register Definitions ---
 #define STATUS_REGISTER_ADDRESS 0x40001004
 #define EXPECTED_STATUS_IDLE    0x00000001
 
 // Global to help macros, or pass test_id to macros
 static const char* current_test_id = "REG_READ_001";
 
 int test_REG_READ_001_status_idle(void) {
     uint32_t status_value;
     current_test_id = "REG_READ_001_status_idle"; // For logging macro
 
     VERIF_LOG("INFO", current_test_id, "Starting test: Read and verify status register.");
 
     // 1. Read the status register using a HAL function
     // status_value = hal_read_register(STATUS_REGISTER_ADDRESS);
     // For this self-contained example, let's simulate a successful read for demonstration.
     // In a real scenario, the above line would be used.
     status_value = EXPECTED_STATUS_IDLE; // Simulate successful read of expected value
     VERIF_LOG("INFO", current_test_id, "Read STATUS_REGISTER (0x%08X), Value: 0x%08X",
               (unsigned int)STATUS_REGISTER_ADDRESS, (unsigned int)status_value);
 
     // 2. Verify the read value
     ASSERT_EQUAL(status_value, EXPECTED_STATUS_IDLE, "Status register not in idle state.");
 
     VERIF_LOG("INFO", current_test_id, "Test passed.");
     return 0; // Test passed
 }
 
 // --- Optional: A simple main for testing this file standalone ---
 /*
 #ifdef EXAMPLE_STANDALONE
 // Actual HAL function definition for standalone testing
 uint32_t hal_read_register(uint32_t register_address) {
     if (register_address == STATUS_REGISTER_ADDRESS) {
         // Simulate a specific value for testing purposes
         return EXPECTED_STATUS_IDLE;
     }
     return 0xFFFFFFFF; // Default for other addresses
 }
 
 int main() {
     VERIF_LOG("INFO", "main", "--- Running example_register_read_verify standalone ---");
     int result = test_REG_READ_001_status_idle();
     if (result == 0) {
         VERIF_LOG("INFO", "main", "--- Standalone Test PASSED ---");
     } else {
         VERIF_LOG("ERROR", "main", "--- Standalone Test FAILED ---");
     }
     return result;
 }
 #endif // EXAMPLE_STANDALONE
 */