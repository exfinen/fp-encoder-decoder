#!/opt/homebrew/bin/python3

import sys

# configuration for Float32 (1 + 23 + 8 = 32)
S_LEN = 1   # unused
F_LEN = 23
E_LEN = 8
BIAS = 127

def int_to_bin(i: int) -> list[int]:
    bits = []
    while i > 0:
        if i % 2 == 1: # if odd
            bits.append(1)
            i = (i - 1) // 2
        else: # if even
            bits.append(0)
            i = i // 2
    bits.reverse()
    return bits

# in case f is tiny, this can return a list with all zeros for non-zero f
def frac_to_bin(f: int) -> list[int]:
    denominator = 10 ** len(str(f))

    # * 2 to handle the case where normalization later removes leading 0 bits
    max_attempt = F_LEN * 2 
    bits = []
    while max_attempt > 0:
        f *= 2
        if f >= denominator:
            bits.append(1)
            f -= denominator
        else:
            bits.append(0)
        max_attempt -= 1
        if f == 0:  # exit if franctional part is zero
            break
    return bits

def bin_to_int(bits: list[int]) -> int:
    n = 0
    for b in bits:
        n = n * 2 + b
    return n

def ieee754_round_up(F: list[int]) -> tuple[list[int], bool]:
    # scan F from the least significat to the most significant bits
    for i in range(len(F) - 1, -1, -1):
        b = F[i]
        if b == 0:
            F[i] = 1 
            return F, False
        else: # if b == 1
            F[i] = 0
    return F, True

# IEEE 754 round-to-nearest, ties-to-even
def apply_ieee754(F: list[int], discarded_bits: list[int]) -> tuple[list[int], bool]:
    overflow = False
    if discarded_bits:
        head = discarded_bits[0]
        rest = discarded_bits[1:]
        if head == 1:
            if any(rest): # above half if the rest is not all zero
                round_up = True
            else: # otherwise exactly half. round up if the last bit of F is set
                round_up = F[-1] == 1
        else: # below half if head is not set
            round_up = False
        if round_up:
            F, overflow = ieee754_round_up(F)
    return F, overflow

def num_str_to_S_F_E(s: str) -> tuple[int, list[int], list[int]]:
    S = int(s.startswith('-'))
    if S == 1:
        s = s[1:]
    dot_idx = s.find('.')
    if dot_idx == -1:
        i = int(s)
        f = 0
    else:
        i = int(s[0:dot_idx])
        f = int(s[dot_idx + 1:])

    int_bits = int_to_bin(i)
    frac_bits = frac_to_bin(f)
    bits = int_bits + frac_bits

    if i == 0 and f == 0:
        return 0, [0] * F_LEN, [0] * E_LEN
    if i > 0:
        E_int = len(int_bits) - 1
        bits = bits[1:]
    else:
        first_1 = frac_bits.index(1)
        first_1_bits = first_1 + 1
        E_int = -first_1_bits
        bits = frac_bits[first_1_bits:]
    E_int += BIAS # add offset to consider BIAS as zero

    print(f"int_bits: {int_bits}")
    print(f"frac_bits: {frac_bits}")

    F = bits[:F_LEN]
    discarded_bits: list[int] = bits[F_LEN:]
    # pad zeros to make len(F) F_LEN
    F += [0] * (F_LEN - len(F)) 

    F, overflow = apply_ieee754(F, discarded_bits)
    if overflow:
        E_int += 1
        F = [0] * F_LEN  # F should become all zero
    E = int_to_bin(E_int)
    E = [0] * (E_LEN - len(E)) + E  # add zero-padding

    return int(S) , F, E

def S_F_E_to_num_str(S: int, F: list[int], E: list[int]) -> str:
    bits = [1] + F
    exp = bin_to_int(E) - BIAS

    if exp >= 0:
        split_idx = exp + 1
        i_bits = bits[:split_idx]
        f_bits = bits[split_idx:]
    else:
        i_bits = []
        f_bits = [0] * (-exp - 1) + bits

    i = bin_to_int(i_bits)

    # f_bits represets the factional part.
    # for example, for 0.25, f_bits = [0, 1]
    # 0.25 = 0 * 2^-1 + 1 * 2^-2
    #
    # but bin_to_int interprets f_bits as a binary integer:
    # 1 = 0 * 2^1 + 1 * 2^0
    #
    # i.e. it returns 2^len(f_bits) * expected fractional value 
    #
    # 0.25 * 2^2
    # = (0 * 2^-1 + 1 * 2^-2*) * 2^2
    # = 0 * 2^1 + 1 * 2^0 
    # = 1
    #
    # so dividing the returned value by 2^len(f_bits) gives the expected value
    #
    # let n = bin_to_int(f_bits) and k = len(f_bits). 
    # then the n / 2^k is the expected value
    # to make this decimal based, 2^k needs to be converted to 10^k
    #
    # since 2^k * x = 10^k, x = 10^k / 2^k and x = 5^k.
    # so multiplying the n by 5^k makes gives decimal-based numerator

    k = len(f_bits)
    n = bin_to_int(f_bits)
    frac = str(n * (5 ** k)).zfill(k) # zfill pads the leading zeros if needed

    print(f"i = {i}")
    print(f"f = {frac}")
    s = f"{i}.{frac}" 
    if S == 1:
        s = '-' + s
    return s

if len(sys.argv) < 2:
    exit(f"Usage: {sys.argv[0]} number")

n = sys.argv[1]
print(f"N = {n}")
S, F, E = num_str_to_S_F_E(n)

print(f"S = {S}")
print(f"F = {F}")
print(f"E = {E}")

n = S_F_E_to_num_str(S, F, E)
print(f"N (Recovered) = {n}")

