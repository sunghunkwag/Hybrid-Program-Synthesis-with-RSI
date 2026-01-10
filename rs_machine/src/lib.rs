use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
#[pyclass]
struct Instruction {
    #[pyo3(get, set)]
    op: String,
    #[pyo3(get, set)]
    a: i32,
    #[pyo3(get, set)]
    b: i32,
    #[pyo3(get, set)]
    c: i32,
}

#[pymethods]
impl Instruction {
    #[new]
    fn new(op: String, a: i32, b: i32, c: i32) -> Self {
        Instruction { op, a, b, c }
    }
}

// Internal enum for faster dispatch
#[derive(Clone, Copy, Debug)]
enum OpCode {
    MOV, SET, SWAP,
    ADD, SUB, MUL, DIV, INC, DEC,
    LOAD, STORE, LDI, STI,
    JMP, JZ, JNZ, JGT, JLT,
    CALL, RET, HALT,
    UNKNOWN,
}

impl From<&str> for OpCode {
    fn from(s: &str) -> Self {
        match s {
            "MOV" => OpCode::MOV,
            "SET" => OpCode::SET,
            "SWAP" => OpCode::SWAP,
            "ADD" => OpCode::ADD,
            "SUB" => OpCode::SUB,
            "MUL" => OpCode::MUL,
            "DIV" => OpCode::DIV,
            "INC" => OpCode::INC,
            "DEC" => OpCode::DEC,
            "LOAD" => OpCode::LOAD,
            "STORE" => OpCode::STORE,
            "LDI" => OpCode::LDI,
            "STI" => OpCode::STI,
            "JMP" => OpCode::JMP,
            "JZ" => OpCode::JZ,
            "JNZ" => OpCode::JNZ,
            "JGT" => OpCode::JGT,
            "JLT" => OpCode::JLT,
            "CALL" => OpCode::CALL,
            "RET" => OpCode::RET,
            "HALT" => OpCode::HALT,
            _ => OpCode::UNKNOWN,
        }
    }
}

#[derive(Clone)]
struct FastInstruction {
    op: OpCode,
    a: i32,
    b: i32,
    c: i32,
}

#[pyclass]
struct ExecutionState {
    #[pyo3(get)]
    regs: Vec<f64>,
    #[pyo3(get)]
    memory: HashMap<i32, f64>,
    #[pyo3(get)]
    pc: i32,
    #[pyo3(get)]
    stack: Vec<i32>,
    #[pyo3(get)]
    steps: i32,
    #[pyo3(get)]
    halted: bool,
    #[pyo3(get)]
    halted_cleanly: bool,
    #[pyo3(get)]
    error: Option<String>,
    #[pyo3(get)]
    trace: Vec<i32>,
    #[pyo3(get)]
    visited_pcs: HashSet<i32>,
    #[pyo3(get)]
    loops_count: i32,
    #[pyo3(get)]
    conditional_branches: i32,
    #[pyo3(get)]
    max_call_depth: i32,
    #[pyo3(get)]
    memory_reads: i32,
    #[pyo3(get)]
    memory_writes: i32,
}

#[pymethods]
impl ExecutionState {
    #[new]
    fn new(regs: Vec<f64>, memory: HashMap<i32, f64>) -> Self {
        ExecutionState {
            regs,
            memory,
            pc: 0,
            stack: Vec::new(),
            steps: 0,
            halted: false,
            halted_cleanly: false,
            error: None,
            trace: Vec::new(),
            visited_pcs: HashSet::new(),
            loops_count: 0,
            conditional_branches: 0,
            max_call_depth: 0,
            memory_reads: 0,
            memory_writes: 0,
        }
    }

    fn fingerprint(&self) -> (i32, i32, i32, i32, i32) {
        (
            self.loops_count.min(20),
            self.conditional_branches.min(20),
            self.memory_writes.min(50),
            self.memory_reads.min(50),
            self.max_call_depth.min(10),
        )
    }
}

#[pyclass]
struct VirtualMachine {
    max_steps: i32,
    memory_size: i32,
    stack_limit: i32,
}

#[pymethods]
impl VirtualMachine {
    #[new]
    fn new(max_steps: i32, memory_size: i32, stack_limit: i32) -> Self {
        VirtualMachine {
            max_steps,
            memory_size,
            stack_limit,
        }
    }

    fn reset(&self, inputs: Vec<f64>) -> ExecutionState {
        let mut regs = vec![0.0; 8];
        let mut memory = HashMap::new();
        
        for (i, v) in inputs.iter().enumerate() {
            if i < self.memory_size as usize {
                memory.insert(i as i32, *v);
            }
        }
        regs[1] = inputs.len() as f64;
        
        ExecutionState::new(regs, memory)
    }

    fn execute(&self, instructions: Vec<Bound<Instruction>>, inputs: Vec<f64>) -> ExecutionState {
        // Pre-convert instructions to internal FastInstruction for speed
        let code: Vec<FastInstruction> = instructions.iter().map(|i| {
            let i = i.borrow();
            FastInstruction {
                op: OpCode::from(i.op.as_str()),
                a: i.a,
                b: i.b,
                c: i.c,
            }
        }).collect();

        let mut st = self.reset(inputs);
        let len = code.len() as i32;
        let mut recent_hashes: Vec<u64> = Vec::new();

        while !st.halted && st.steps < self.max_steps {
            if st.pc < 0 || st.pc >= len {
                st.halted = true;
                st.halted_cleanly = true;
                break;
            }

            st.visited_pcs.insert(st.pc);
            st.trace.push(st.pc);
            let prev_pc = st.pc;
            let inst = &code[st.pc as usize];
            st.steps += 1;

            // Degenerate loop detection
            // Note: Simplistic hashing for demonstration, matches Python's tuple hash intent
            use std::hash::{Hash, Hasher};
            use std::collections::hash_map::DefaultHasher;
            let mut hasher = DefaultHasher::new();
            st.pc.hash(&mut hasher);
            // Hash first 4 regs as integers
            for r in st.regs.iter().take(4) {
                (*r as i32).hash(&mut hasher);
            }
            st.stack.len().hash(&mut hasher);
            let state_sig = hasher.finish();

            recent_hashes.push(state_sig);
            if recent_hashes.len() > 25 {
                recent_hashes.remove(0);
                let unique_count = recent_hashes.iter().collect::<HashSet<_>>().len();
                if unique_count < 3 {
                    st.error = Some("DEGENERATE_LOOP".to_string());
                    st.halted = true;
                    break;
                }
            }

            // Step execution
            self.step(&mut st, inst);
            
            if st.halted {
                break;
            }

             // Stats
            if st.pc <= prev_pc && !st.halted {
                st.loops_count += 1;
            }
            if matches!(inst.op, OpCode::JZ | OpCode::JNZ | OpCode::JGT | OpCode::JLT) {
                st.conditional_branches += 1;
            }
            st.max_call_depth = st.max_call_depth.max(st.stack.len() as i32);
        }

        st
    }
}

impl VirtualMachine {
    fn step(&self, st: &mut ExecutionState, inst: &FastInstruction) {
        let op = inst.op;
        let a = inst.a;
        let b = inst.b;
        let c = inst.c;

        let clamp = |x: f64| -> f64 {
            if x.is_nan() || x.is_infinite() {
                0.0
            } else {
                x.max(-1e9).min(1e9)
            }
        };

        let addr = |x: f64| -> i32 {
            let idx = x as i32;
            idx.max(0).min(self.memory_size - 1)
        };

        let mut jump = false;

        match op {
            OpCode::HALT => {
                st.halted = true;
                st.halted_cleanly = true;
                return;
            }
            OpCode::SET => {
                st.regs[(c % 8).abs() as usize] = a as f64;
            }
            OpCode::MOV => {
                st.regs[(c % 8).abs() as usize] = st.regs[(a % 8).abs() as usize];
            }
            OpCode::SWAP => {
                let ra = (a % 8).abs() as usize;
                let rb = (b % 8).abs() as usize;
                let tmp = st.regs[ra];
                st.regs[ra] = st.regs[rb];
                st.regs[rb] = tmp;
            }
            OpCode::ADD => {
                let ra = (a % 8).abs() as usize;
                let rb = (b % 8).abs() as usize;
                st.regs[(c % 8).abs() as usize] = clamp(st.regs[ra] + st.regs[rb]);
            }
            OpCode::SUB => {
                let ra = (a % 8).abs() as usize;
                let rb = (b % 8).abs() as usize;
                st.regs[(c % 8).abs() as usize] = clamp(st.regs[ra] - st.regs[rb]);
            }
            OpCode::MUL => {
                let ra = (a % 8).abs() as usize;
                let rb = (b % 8).abs() as usize;
                st.regs[(c % 8).abs() as usize] = clamp(st.regs[ra] * st.regs[rb]);
            }
            OpCode::DIV => {
                let ra = (a % 8).abs() as usize;
                let rb = (b % 8).abs() as usize;
                let den = st.regs[rb];
                if den.abs() > 1e-9 {
                    st.regs[(c % 8).abs() as usize] = clamp(st.regs[ra] / den);
                } else {
                    st.regs[(c % 8).abs() as usize] = 0.0;
                }
            }
            OpCode::INC => {
                let rc = (c % 8).abs() as usize;
                st.regs[rc] = clamp(st.regs[rc] + 1.0);
            }
            OpCode::DEC => {
                let rc = (c % 8).abs() as usize;
                st.regs[rc] = clamp(st.regs[rc] - 1.0);
            }
            OpCode::LOAD => {
                let idx = addr(st.regs[(a % 8).abs() as usize]);
                st.memory_reads += 1;
                st.regs[(c % 8).abs() as usize] = *st.memory.get(&idx).unwrap_or(&0.0);
            }
            OpCode::STORE => {
                let idx = addr(st.regs[(a % 8).abs() as usize]);
                st.memory_writes += 1;
                let val = clamp(st.regs[(c % 8).abs() as usize]);
                st.memory.insert(idx, val);
            }
            OpCode::LDI => {
                let base = addr(st.regs[(a % 8).abs() as usize]);
                let off = addr(st.regs[(b % 8).abs() as usize]);
                let target = addr((base + off) as f64);
                st.memory_reads += 1;
                st.regs[(c % 8).abs() as usize] = *st.memory.get(&target).unwrap_or(&0.0);
            }
            OpCode::STI => {
                let base = addr(st.regs[(a % 8).abs() as usize]);
                let off = addr(st.regs[(b % 8).abs() as usize]);
                let target = addr((base + off) as f64);
                st.memory_writes += 1;
                let val = clamp(st.regs[(c % 8).abs() as usize]);
                st.memory.insert(target, val);
            }
            OpCode::JMP => {
                st.pc += a;
                jump = true;
            }
            OpCode::JZ => {
                if st.regs[(a % 8).abs() as usize].abs() < 1e-9 {
                    st.pc += b;
                    jump = true;
                }
            }
            OpCode::JNZ => {
                if st.regs[(a % 8).abs() as usize].abs() >= 1e-9 {
                    st.pc += b;
                    jump = true;
                }
            }
            OpCode::JGT => {
                if st.regs[(a % 8).abs() as usize] > st.regs[(b % 8).abs() as usize] {
                    st.pc += c;
                    jump = true;
                }
            }
            OpCode::JLT => {
                if st.regs[(a % 8).abs() as usize] < st.regs[(b % 8).abs() as usize] {
                    st.pc += c;
                    jump = true;
                }
            }
            OpCode::CALL => {
                 if st.stack.len() as i32 >= self.stack_limit {
                    st.error = Some("STACK_OVERFLOW".to_string());
                    st.halted = true;
                    return;
                }
                st.stack.push(st.pc + 1);
                st.pc += a;
                jump = true;
            }
            OpCode::RET => {
                if let Some(ret_pc) = st.stack.pop() {
                    st.pc = ret_pc;
                    jump = true;
                } else {
                    st.halted = true;
                    st.halted_cleanly = true;
                    jump = true;
                }
            }
             _ => {
                st.error = Some("UNKNOWN_OP".to_string());
                st.halted = true;
                return;
            }
        }

        if !jump {
            st.pc += 1;
        }
    }
}

#[pymodule]
fn rs_machine(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Instruction>()?;
    m.add_class::<ExecutionState>()?;
    m.add_class::<VirtualMachine>()?;
    Ok(())
}
