// Precomputed LUTs for 0.1° resolution
const _sin_lut = Array.from({length: 3600}, (_, i) => 
    Math.round(Math.sin(Math.PI * i / 1800) * 1000)
);

export const config = {
    id: "fast_math",
    name: "Fast Trigonometry",
    category: "utils",
    description: "High-speed sin/cos calculations",
    inputs: [
        { id: "angle", label: "Angle (degrees)", type: "number", value: 45 }
    ]
};

export function process(input_data) {
    const angle = input_data["angle"] % 360;
    const idx = Math.floor(angle * 10);
    return {
        sin: _sin_lut[idx] / 1000,
        cos: _sin_lut[(idx + 900) % 3600] / 1000
    };
}
