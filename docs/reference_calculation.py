"""Independent reference values for the Lab 03 A1-A5 acceptance cases.

This script deliberately does NOT import app.py, bjt_bias.py or dc_bias.py.
It is a direct transcription of the equations on the lab sheet using plain
floats, so the expected results stay independent of the code under test.

Shared: VCC = 12 V, RC = 2.2 kOhm, beta = 100, VBE = 0.70 V.
Resistances below are entered in ohms (1 MOhm = 1e6 ohm, 1 kOhm = 1e3 ohm).
"""

VCC = 12.0
RC = 2200.0
BETA = 100.0
VBE = 0.70


def from_base(ib, re):
    ic = BETA * ib
    ie = (BETA + 1) * ib
    ve = ie * re
    vb = ve + VBE
    vc = VCC - ic * RC
    vce = vc - ve
    return dict(ib_ua=ib * 1e6, ic_ma=ic * 1e3, ie_ma=ie * 1e3,
                vb_v=vb, ve_v=ve, vc_v=vc, vce_v=vce)


def divider(r1, r2, re):
    vth = VCC * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)
    ib = (vth - VBE) / (rth + (BETA + 1) * re)
    return dict(vth_v=vth, rth_ohm=rth, **from_base(ib, re))


def fixed(rb):
    ib = (VCC - VBE) / rb
    return from_base(ib, 0.0)


def emitter(rb, re):
    ib = (VCC - VBE) / (rb + (BETA + 1) * re)
    return from_base(ib, re)


def show(case, result):
    print(case)
    for key, value in result.items():
        print(f"  {key:>10s} = {value:.9f}")


show("A1 Divider R1=100k R2=22k RE=1k", divider(100000.0, 22000.0, 1000.0))
show("A2 Fixed RB=1M", fixed(1000000.0))
show("A3 Emitter RB=1M RE=1k", emitter(1000000.0, 1000.0))
show("A4 Emitter RB=1M RE=2k", emitter(1000000.0, 2000.0))
