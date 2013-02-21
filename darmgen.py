import darmtbl
import itertools
import sys
import textwrap


def instruction_name(x):
    return x.split('{')[0].split('<')[0].split()[0]


def instruction_names(arr):
    """List of all unique instruction names."""
    return ['INVLD'] + sorted(set(instruction_name(x) for x in arr))


def instruction_names_enum(arr):
    """Enumeration of all instruction names."""
    text = ', '.join('I_%s' % x for x in instruction_names(arr))
    text = '\n    '.join(textwrap.wrap(text, 74))
    return 'typedef enum {\n    %s\n} armv7_instr_t;\n' % text


def instruction_names_table(arr):
    """Table of strings of all instructions."""
    text = ', '.join('"%s"' % x for x in instruction_names(arr))
    text = '\n    '.join(textwrap.wrap(text, 74))
    return 'const char *armv7_mnemonics[] = {\n    %s\n};' % text


def updates_condition_flags(arr):
    """List of all instructions that have the S flag."""
    return sorted(set(instruction_name(x[0]) for x in arr if darmtbl.S in x))


def updates_condition_flags_table(arr):
    """Lookup table returning True for instructions that have the S flag."""
    names = instruction_names(arr)
    flags = updates_condition_flags(arr)
    table = ', '.join(('1' if x in flags else '0') for x in names)
    text = '\n    '.join(textwrap.wrap(table, 74))
    return 'uint8_t updates_condition_flags[] = {\n    %s\n};' % text


def instruction_types_table(arr):
    """Lookup table for the types of instructions."""
    table = ', '.join(str(arr[x][0]) if x in arr else 'T_INVLD'
                      for x in xrange(256))
    text = '\n    '.join(textwrap.wrap(table, 74))
    return 'armv7_enctype_t armv7_instr_types[] = {\n    %s\n};\n' % text


def instruction_names_index_table(arr):
    """Lookup table for instruction label for each instruction index."""
    table = ', '.join('I_%s' % str(arr[x][1]) if x in arr else 'I_INVLD'
                      for x in xrange(256))
    text = '\n    '.join(textwrap.wrap(table, 74))
    return 'armv7_instr_t armv7_instr_labels[] = {\n    %s\n};\n' % text


def type_lookup_table(name, *args):
    """Create a lookup table for a certain instruction type."""
    table = ', '.join('I_%s' % x.upper() if x else 'I_INVLD' for x in args)
    text = '\n    '.join(textwrap.wrap(table, 74))
    return 'armv7_instr_t %s_instr_lookup[] = {\n    %s\n};\n' % (name, text)


def type_encoding_info(enumname, arr):
    text = []
    for name, info, encodings, fn in arr:
        text.append(
            '    // info:\n' +
            '    // %s\n    //\n' % info +
            '    // encodings:\n    // ' +
            '\n    // '.join(encodings) + '\n' +
            '    T_%s,' % name)

    return 'typedef enum _%s_t {\n%s\n} %s_t;\n' % (enumname,
                                                    '\n\n'.join(text),
                                                    enumname)

d = darmtbl

# we specify various instruction types
cond_instr_types = [
    ('INVLD', 'Invalid or non-existent type',
     ['I_INVLD'], lambda x, y, z: False),
    ('ARITH_SHIFT',
     'Arithmetic instructions which take a shift for the second source',
     ['ins{S}<c> <Rd>,<Rn>,<Rm>{,<shift>}',
      'ins{S}<c> <Rd>,<Rn>,<Rm>,<type> <Rs>'],
     lambda x, y, z: d.Rn in x and d.Rd in x and x[-3] == d.type_
     and x[-1] == d.Rm),
    ('ARITH_IMM',
     'Arithmetic instructions which take an immediate as second source',
     ['ins{S}<c> <Rd>,<Rn>,#<const>'],
     lambda x, y, z: d.Rn in x and d.Rd in x and d.imm12 in x),
    ('BRNCHSC', 'Branch and System Call instructions',
     ['B(L)<c> <label>', 'SVC<c> #<imm24>'],
     lambda x, y, z: x[-1] == d.imm24),
    ('BRNCHMISC', 'Branch and Misc instructions',
     ['B(L)X(J)<c> <Rm>', 'BKPT #<imm16>', 'MSR<c> <spec_reg>,<Rn>'],
     lambda x, y, z: x[1:9] == (0, 0, 0, 1, 0, 0, 1, 0)),
    ('MOV_IMM', 'Move immediate to a register (possibly negating it)',
     ['ins{S}<c> <Rd>,#<const>'],
     lambda x, y, z: x[-1] == d.imm12 and x[-2] == d.Rd),
    ('CMP_OP', 'Comparison instructions which take two operands',
     ['ins<c> <Rn>,<Rm>{,<shift>}', 'ins<c> <Rn>,<Rm>,<type> <Rs>'],
     lambda x, y, z: x[-1] == d.Rm and x[-3] == d.type_ and
        (x[-4] == d.imm5 and x[-8:-4] == (0, 0, 0, 0) or
         x[-5] == d.Rs and x[-9:-5] == (0, 0, 0, 0))),
    ('CMP_IMM', 'Comparison instructions which take an immediate',
     ['ins<c> <Rn>,#<const>'],
     lambda x, y, z: x[-1] == d.imm12 and x[-6] == d.Rn),
    ('OPLESS', 'Instructions which don\'t take any operands',
     ['ins<c>'],
     lambda x, y, z: len(x) == 29),
    ('DST_SRC', 'Manipulate and move a register to another register',
     ['ins{S}<c> <Rd>,<Rm>', 'ins{S}<c> <Rd>,<Rm>,#<imm>',
     'ins{S}<c> <Rd>,<Rn>,<Rm>'],
     lambda x, y, z: z == 26 or z == 27),
]

if __name__ == '__main__':
    uncond_table = {}
    cond_table = {}
    for description in darmtbl.ARMv7:
        instr = description[0]
        bits = description[1:]

        identifier = []
        remainder = []
        for x in xrange(1 if bits[0] == darmtbl.cond else 4, len(bits)):
            if isinstance(bits[x], int):
                identifier.append(str(bits[x]))
            elif len(identifier) + bits[x].bitsize > 8:
                identifier += ['01'] * (8-len(identifier))
                remainder = bits[x:]
                break
            else:
                identifier += ['01'] * bits[x].bitsize

        for x in itertools.product(*identifier[:8]):
            idx = sum(int(x[y])*2**(7-y) for y in xrange(8))

            # for each conditional instruction, check which type of
            # instruction this is
            for instr_idx, y in enumerate(cond_instr_types):
                if bits[0] == d.cond and y[3](bits, instr, idx):
                    cond_table[idx] = instr_idx, instruction_name(instr)
                    break

    # python magic!
    sys.stdout = open(sys.argv[1], 'w')

    if sys.argv[1][-2:] == '.h':

        # print required headers
        print '#ifndef __ARMV7_TBL__'
        print '#define __ARMV7_TBL__'
        print
        print '#include <stdint.h>'
        print

        # print all instruction labels
        print instruction_names_enum(open('instructions.txt'))

        # print type info for each encoding type
        print type_encoding_info('armv7_enctype', cond_instr_types)

        # print some required definitions
        print 'armv7_enctype_t armv7_instr_types[256];'
        print 'armv7_instr_t armv7_instr_labels[256];'
        print 'armv7_instr_t type_shift_instr_lookup[16];'
        print 'armv7_instr_t type4_instr_lookup[16];'
        print 'armv7_instr_t type_opless_instr_lookup[8];'
        print

        print '#endif'
        print

    elif sys.argv[1][-2:] == '.c':

        # print a header
        print '#include <stdio.h>'
        print '#include <stdint.h>'
        print '#include "%s"' % (sys.argv[1][:-2] + '.h')
        print

        # print a table containing all the types of instructions
        print instruction_types_table(cond_table)

        # print a table containing the instruction label for each entry
        print instruction_names_index_table(cond_table)

        # print a lookup table for the shift type (which is a sub-type of
        # the dst-src type), the None types represent instructions of the
        # STR family, which we'll handle in the next handler, T_STR.
        t_shift = {
            0b0000: 'lsl',
            0b0001: 'lsl',
            0b0010: 'lsr',
            0b0011: 'lsr',
            0b0100: 'asr',
            0b0101: 'asr',
            0b0110: 'ror',
            0b0111: 'ror',
            0b1000: 'lsl',
            0b1001: None,
            0b1010: 'lsr',
            0b1011: None,
            0b1100: 'asr',
            0b1101: None,
            0b1110: 'ror',
            0b1111: None}

        print type_lookup_table('type_shift',
                                *[t_shift[x] for x in xrange(16)])

        t4 = 'msr', 'bx', 'bxj', 'blx', None, 'qsub', None, 'bkpt', 'smlaw', \
            None, 'smulw', None, 'smlaw', None, 'smulw', None
        print type_lookup_table('type4', *t4)

        t_opless = 'nop', 'yield', 'wfe', 'wfi', 'sev', None, None, None
        print type_lookup_table('type_opless', *t_opless)
