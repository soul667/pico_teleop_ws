# VR controller button event
std_msgs/Header header

# Which hand: "left" | "right"
string hand

# Button name: "trigger" | "grip" | "thumbstick" | "a" | "b" | "x" | "y" | "menu"
string button

# Event type: "pressed" | "released" | "value_changed"
string event

# Analog value (0.0 - 1.0 for trigger/grip, -1.0 to 1.0 for thumbstick axes)
float64 value

# Thumbstick axes (only for thumbstick events)
float64 axis_x
float64 axis_y
