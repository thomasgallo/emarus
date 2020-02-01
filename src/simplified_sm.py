#!/usr/bin/env python


import rospy
import sys
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
from emarus.msg import camera

class StateMachine:

  def __init__(self):

    # Subscriber and publisher needed
    self.sub_ = rospy.Subscriber("/camera_node/visual_recognition",camera,self.callback) # Subscribe to the camera's topic
    self.speed_ = rospy.Publisher("cmd_vel", Twist, queue_size = 10)    # Publish the velocity to send to the motor driver
    self.nh_ = rospy.init_node('simplified_sm', anonymous=True)

    ## IMPORTANT ##
    # List of the possible states, write here to add one
    self.states_ = ['FINDINGGOAL','FINDINGBALL','TARGETINGBALL','KICKINGBALL']
    self.currentState_ = 0  # Cursor on the current state

    # Global variables
    self.amplitude_ = 1 # amplitude of the rotation around the z-axis
    self.threshold_angle_ = 10  # minimal accepted angle between the robot and the ball
    self.threshold_distance_ = 10 # minimal accepted distance between the robot and the ball
    self.coefficient_ = 0.01    # Coefficient corresponding to the amplitude of the movement along the y axis
    self.ball_distance_ = 0 # Distance between the ball and the robot in m
    self.error_ball_ = 0    # Difference in pixel between the robot and the ball
    self.error_goal_ = 0    # Difference in pixel between the robot and the goal
    self.isBallVisible_ = False
    self.isGoalVisible_ = False
    self.vel_msg_ = Twist() # Msg that will be published to the Arduino


  def callback(self,data):
    # Get the data from the camera node
    self.isBallVisible_ = data.ball_seen
    self.isGoalVisible_ = data.goal_seen
    self.ball_distance_ = data.ball_distance
    self.error_ball_ = data.error_ball
    self.error_goal_ = data.error_goal
    self.decision()

  def decision(self):
    rospy.loginfo("decision making")
    #rospy.loginfo("currentState_ avant = %d",self.currentState_)

    if(self.currentState_ == self.states_.index("FINDINGGOAL")):
        rospy.loginfo("FINDINGGOAL")
        # If the goal is not visible, rotate until finding it
        if self.isGoalVisible_ == False:
            self.vel_msg_.angular.z = self.amplitude_
        # else, go to the next state FINDINGBALL
        else:
            self.currentState_ = self.states_.index("FINDINGBALL")

    elif(self.currentState_ == self.states_.index("FINDINGBALL")):
        rospy.loginfo("FINDINGBALL")
        # If the ball is not visible, rotate until finding it
        if self.isBallVisible_ == False:
            self.vel_msg_.angular.z = self.amplitude_
        # else, go to the next state TARGETINGBALL
        else:
            self.currentState_ = self.states_.index("TARGETINGBALL")

    elif(self.currentState_ == self.states_.index("TARGETINGBALL")):
        rospy.loginfo("TARGETINGBALL")
        # If the ball is visible, modify the orientation to face the ball and move towards the ball
        if self.isBallVisible_ == True:
            # Define the orientation of the robot if it is sufficiently misaligned
            if self.error_ball_ > self.threshold_angle_:
                self.vel_msg_.angular.z = self.error_ball_*self.coefficient_
            # Define the linear speed of the robot if it is not close enough
            if self.ball_distance_ > self.threshold_distance_:
                self.vel_msg_.linear.y = self.ball_distance_*self.coefficient_
            # If the robot is weill positionned to kick
            if self.error_ball_ < self.threshold_angle_ and self.ball_distance_ < self.threshold_distance_:
                self.currentState_ = self.states_.index("KICKINGBALL")
        # else, go to the state FINDINGBALL
        else:
            self.currentState_ = self.states_.index("FINDINGBALL")

    elif(self.currentState_ == self.states_.index("KICKINGBALL")):
        rospy.loginfo("KICKINGBALL")
        # promptly go to the ball
        self.vel_msg_.linear.y = 10
        self.currentState_ = self.states_.index("FINDINGBALL") # Go back to precedent state

    # In every state, send the velocity to the Arduino and reinitialize the component of the Twist()
    self.speed_.publish(self.vel_msg_)
    self.vel_msg_.linear.y = 0
    self.vel_msg_.angular.z = 0
    #rospy.loginfo("currentState_ apres = %d",self.currentState_)



def main(args):
  sm = StateMachine()   # Initialize the state machine
  try:
    rospy.spin()    # Spin the decision making code
  except KeyboardInterrupt:
    print("Shutting down")

if __name__ == '__main__':
    main(sys.argv)
