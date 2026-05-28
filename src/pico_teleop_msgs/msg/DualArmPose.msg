# Dual arm end-effector poses from VR controllers
std_msgs/Header header

# Left arm target pose
geometry_msgs/PoseStamped left_pose

# Right arm target pose
geometry_msgs/PoseStamped right_pose

# Gripper states (0.0 = closed, 1.0 = open)
float64 left_gripper
float64 right_gripper
