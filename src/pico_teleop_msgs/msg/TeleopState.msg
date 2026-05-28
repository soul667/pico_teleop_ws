# Teleoperation system state
std_msgs/Header header

# Connection status
bool vr_connected
bool robot_connected

# Current IK solver: "curobo" | "moveit" | "trac_ik"
string ik_solver

# Current arm config name
string arm_config

# Control mode: "idle" | "teleop" | "paused"
string control_mode

# Latency metrics (ms)
float64 vr_latency
float64 ik_latency
float64 total_latency

# Safety
bool emergency_stop
bool workspace_limit_reached
