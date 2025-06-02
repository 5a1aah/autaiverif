#ifndef CVA6_HAL_H
#define CVA6_HAL_H

#include <stdint.h>

// RISC-V CSR Access Macros/Functions
// These are typically provided by a lower-level library or defined as inline assembly.
// For HAL purposes, we define function-like signatures.

/**
 * @brief Reads a Control and Status Register (CSR).
 * @param csr_address The address of the CSR to read.
 * @return The value read from the CSR.
 */
uint64_t hal_cva6_read_csr(uint32_t csr_address);

/**
 * @brief Writes a value to a Control and Status Register (CSR).
 * @param csr_address The address of the CSR to write.
 * @param value The value to write to the CSR.
 */
void hal_cva6_write_csr(uint32_t csr_address, uint64_t value);

/**
 * @brief Sets specific bits in a Control and Status Register (CSR).
 * @param csr_address The address of the CSR.
 * @param bit_mask The mask of bits to set.
 */
void hal_cva6_set_csr_bits(uint32_t csr_address, uint64_t bit_mask);

/**
 * @brief Clears specific bits in a Control and Status Register (CSR).
 * @param csr_address The address of the CSR.
 * @param bit_mask The mask of bits to clear.
 */
void hal_cva6_clear_csr_bits(uint32_t csr_address, uint64_t bit_mask);


// Cache Control Functions (Example - actual implementation is highly platform-specific)

/**
 * @brief Flushes the entire Data Cache (D-Cache).
 * This operation ensures that all dirty lines in the D-Cache are written back to main memory.
 * The exact mechanism (e.g., specific instructions or memory-mapped controller) depends on the CVA6 configuration.
 */
void hal_cva6_dcache_flush_all(void);

/**
 * @brief Invalidates the entire Data Cache (D-Cache).
 * This operation marks all D-Cache lines as invalid. Subsequent reads will fetch from main memory.
 */
void hal_cva6_dcache_invalidate_all(void);

/**
 * @brief Flushes a specific address range from the Data Cache (D-Cache).
 * @param start_address The starting memory address of the range to flush.
 * @param size The size of the memory range in bytes.
 */
void hal_cva6_dcache_flush_range(uint64_t start_address, uint32_t size);

/**
 * @brief Invalidates a specific address range in the Data Cache (D-Cache).
 * @param start_address The starting memory address of the range to invalidate.
 * @param size The size of the memory range in bytes.
 */
void hal_cva6_dcache_invalidate_range(uint64_t start_address, uint32_t size);

/**
 * @brief Invalidates the entire Instruction Cache (I-Cache).
 * Ensures that subsequent instruction fetches load fresh instructions from memory.
 * Often involves a `FENCE.I` instruction or similar mechanism.
 */
void hal_cva6_icache_invalidate_all(void);


// Basic Peripheral Interaction (Example - assumes memory-mapped peripherals)
/**
 * @brief Writes a 32-bit value to a memory-mapped peripheral register.
 * @param base_address The base address of the peripheral.
 * @param offset The offset of the register within the peripheral's address space.
 * @param value The 32-bit value to write.
 */
void hal_cva6_mmio_write32(uint64_t base_address, uint32_t offset, uint32_t value);

/**
 * @brief Reads a 32-bit value from a memory-mapped peripheral register.
 * @param base_address The base address of the peripheral.
 * @param offset The offset of the register within the peripheral's address space.
 * @return The 32-bit value read from the register.
 */
uint32_t hal_cva6_mmio_read32(uint64_t base_address, uint32_t offset);


// WFI - Wait For Interrupt
/**
 * @brief Executes the WFI (Wait For Interrupt) instruction.
 * Puts the core in a low-power state until an interrupt occurs.
 */
void hal_cva6_wfi(void);

#endif // CVA6_HAL_H