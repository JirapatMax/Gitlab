import math


def analyze_dc(voltage_v, resistance_ohm):
    try:
        voltage_v = float(voltage_v)
        resistance_ohm = float(resistance_ohm)
    except (TypeError, ValueError) as error:
        raise ValueError("Voltage and resistance must be numbers.") from error

    if not math.isfinite(voltage_v) or not math.isfinite(resistance_ohm):
        raise ValueError("Voltage and resistance must be finite numbers.")
    if resistance_ohm <= 0:
        raise ValueError("Resistance must be greater than zero.")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    try:
        voltage = input("Voltage (V): ")
        resistance = input("Resistance (ohm): ")
        result = analyze_dc(voltage, resistance)
    except ValueError as error:
        print(f"Error: {error}")
        raise SystemExit(1)

    print(f"Current: {result['current_a']} A")
    print(f"Power: {result['power_w']} W")