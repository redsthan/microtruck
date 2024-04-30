from typing import Any, List
from collections import deque
#from machine import Pin

ERROR = ... #Pin('LED', Pin.OUT)

class Instruction:
    def __init__(self, doctet: List[int]) -> None:
        self.opcode = doctet[0]
        match self.opcode:
            case 0x0|0x2|0x3|0xF:
                self.data = doctet[1]<<4 | doctet[2]
            case 0x1|0x4|0x5|0x6|0x7|0x8|0xC:
                self.var1, self.var2 = doctet[1], doctet[2]
            case 0x9:
                self.var1 = doctet[1]
                self.data = doctet[2]
            case 0xA:
                self.data = doctet[1]
                self.var1 = doctet[2]
            case 0xB:
                self.scode = doctet[1]>>2
                self.deque = doctet[1]&0b11
                if self.scode == 0b01:
                    self.extr = bool(doctet[2]&0x1)
            case 0xD|0xE:
                self.scode = doctet[1]
                self.var1 = doctet[2]
                
    def __call__(self, robot: "Robot") -> Any:
        match self.opcode:
            case 0x0:
                robot.EDX(self.data)
            case 0x1:
                robot.MOV(self.var1, self.var2)
            case 0x2:
                robot.JMP(self.data)
            case 0x3:
                robot.JMC(self.data)
            case 0x4:
                robot.AND(self.var1, self.var2)
            case 0x5:
                robot.OR(self.var1, self.var2)
            case 0x6:
                robot.ADD(self.var1, self.var2)
            case 0x7:
                robot.ADC(self.var1, self.var2)
            case 0x8:
                robot.SUB(self.var1, self.var2)
            case 0x9:
                robot.INC(self.var1, self.data)
            case 0xA:
                robot.SHF(self.data, self.var1)
            case 0xB:
                match self.scode:
                    case 0b00:
                        robot.ISE(self.deque)
                    case 0b01:
                        robot.POP(self.deque, self.extr)
                    case 0b10:
                        robot.PSR(self.deque, self.var1)
                    case 0b11:
                        robot.PSL(self.deque, self.var1)
            case 0xC:
                robot.IMP(self.scode, self.var1)
            case 0xD:
                robot.EXP(self.scode, self.var1)
            case 0xE:
                robot.CMP(self.var1)
            case 0xF:
                robot.STP(self.data)
            case _:
                robot.error()

class Program:
    def __init__(self, byt: bytes) -> None:
        dbytes = []
        for b in list(byt):
            dbytes.append(b>>4)
            dbytes.append(b&0xF)
        self.instructions = [Instruction(dbytes[i-2:i+1]) for i in range(2, len(dbytes), 3)]
        
    def __iter__(self):
        for instruction in self.instructions:
            yield instruction

class Robot:
    def __init__(self, program: Program):
        self.registers = [0x00]*16
        self.stacks = [deque() for _ in range(4)]
        self.pc = 0
        self.cr = 0
        self.running = False
        self.program = program
        
    def __call__(self):
        for instruction in self.program:
            if not self.running and instruction.opcode != 0xF:
                break
            instruction(self)
        
    def error(self):
        print("ERROR")
        self.running = False
        #ERROR.value(1)
        
    def EDX(self, data: int):
        print("EDX: ", data)
        self.registers[0] = data
        self.pc += 1
    
    def MOV(self, var1: int, var2: int):
        print("MOV: ", var1, var2)
        self.registers[var1] = self.registers[var2]
        self.pc += 1
    
    def JMP(self, data: int):
        print("JMP: ", data)
        self.pc = data
        
    def JMC(self, data: int):
        print("JMC: ", data)
        if self.registers[0] == 0x0001:
            self.pc = data
    
    def AND(self, var1: int, var2: int):
        print("AND: ", var1, var2)
        self.registers[0] = self.registers[var1] & self.registers[var2]
        self.pc += 1
    
    def OR(self, var1: int, var2: int):
        print("OR: ", var1, var2)
        self.registers[0] = self.registers[var1] | self.registers[var2]
        self.pc += 1
    
    def ADD(self, var1: int, var2: int):
        print("ADD: ", var1, var2)
        a = self.registers[var1] + self.registers[var2]
        self.cr, self.registers[0] = a>>8, a&0xFF
        self.pc += 1
    
    def ADC(self, var1: int, var2: int):
        print("ADC: ", var1, var2)
        a = self.registers[var1] + self.registers[var2] + self.cr
        self.cr, self.registers[0] = a>>8, a&0xFF
        self.pc += 1
        
    def SUB(self, var1: int, var2: int):
        print("SUB: ", var1, var2)
        if self.registers[var1] >= self.registers[var2]:
            self.registers[0] = self.registers[var1]-self.registers[var2]
            self.pc += 1
        else:
            self.error()
            
    def INC(self, var1: int, data: int):
        print("INC: ", var1, data)
        if not data&0x10:
            self.registers[var1] += data
        else:
            self.registers[var1] -= ~data + 1
        self.pc += 1
    
    def SHF(self, data: int, var1: int):
        print("SHF: ", data, var1)
        if data&0x10:
            self.registers[var1] = self.registers[var1]<<data
        else:
            self.registers[var1] = self.registers[var1]>>(~data+1)
        self.pc += 1
        
    def ISE(self, dq: int):
        print("ISE: ", dq)
        if self.stacks[dq]:
            self.registers[0] = 0x01
        else:
            self.registers[0] = 0x00
        self.pc += 1
    
    def POP(self, dq: int, extr: bool):
        print("POP: ", dq, extr)
        if self.stacks[dq] and extr:
            self.registers[0] = self.stacks[dq].pop()
        elif self.stacks[dq]:
            self.stacks[dq].popleft()
        else:
            self.error()
    
    def PSR(self, dq: int, var1: int):
        print("PSR: ", dq, var1)
        self.stacks[dq].append(self.registers[var1])
        self.pc += 1
        
    def PSL(self, dq: int, var1: int):
        print("PSL: ", dq, var1)
        self.stacks[dq].appendleft(self.registers[var1])
        self.pc += 1
        
    def CMP(self, var1: int):
        print("CMP: ", var1)
        if self.registers[var1] == self.registers[0]:
            self.registers[0] = 0x00
        elif self.registers[var1] > self.registers[0]:
            self.registers[0] = 0x01
        else:
            self.registers[0] = 0xFF
        self.pc += 1
        
    def IMP(self, comp: int, var1: int):
        print("IMP: ", comp, var1)
        raise NotImplementedError
    
    def EXP(self, comp: int, var1: int):
        print("EXP: ", comp, var1)
        raise NotImplementedError
    
    def STP(self, data: int):
        print("STP: ", data)
        if data == 0x55:
            self.running = True
            self.pc += 1
        elif data == 0xAA:
            self.running = False
            self.pc += 1
        else:
            self.error()
                
    
    
if __name__ == "__main__":
    byt = b"\xF5\x50\xFF\xFA\xA0"
    prg = Program(byt)
    robot = Robot(prg)
    robot()
    