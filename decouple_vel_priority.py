
import rospy
from geometry_msgs.msg import Twist
from geometry_msgs.msg import PoseStamped

from to_goal import angle_to_goal, go_to_goal
import numpy as np
import matplotlib.pyplot as plt
import time
from tf.transformations import euler_from_quaternion

timefile = open('time.csv','w')
timefile.write('name,time,priority\n')
node = rospy.init_node("avoid_cllision")
rate = rospy.Rate(40)
class Uav:
    
    def __init__(self,name,v,priority,goal):
        self.x = 0
        self.y = 0
        self.yaw = 0
        self.v = v
        self.priority=priority
        self.name=name
        self.pub = rospy.Publisher(str('/'+name+'/cmd_vel'), Twist, queue_size=10)
        self.sub = rospy.Subscriber(str('/'+name+'/ground_truth_to_tf/pose'), PoseStamped, self.poseCallback)
        self.msg = Twist()
        self.goal = goal
        self.file = open(name+'.csv','w')
        self.time=0
        self.check=True
        

    def poseCallback(self, data):
        self.x = data.pose.position.x
        self.y = data.pose.position.y
        self.yaw = euler_from_quaternion([data.pose.orientation.x,data.pose.orientation.y,data.pose.orientation.z,data.pose.orientation.w])[2]

    def go_to_goal(self, goal): #return velocity vector for goal
        dist = np.linalg.norm((goal[0] - self.x, goal[1]-self.y))
        if dist<1:
            return np.array([0,0])
        else:
            angle = np.arctan2(goal[1]-self.y,goal[0]-self.x) 
            return min(self.v,dist)*np.array([np.cos(angle),np.sin(angle)])

    def avoid_collision(self, drones): 
        vec = np.array([0,0],dtype='float64')
        for drone in drones:
            if drone.name != self.name:
                if np.linalg.norm((drone.x-self.x,drone.y-self.y))<(drone.priority)*2:
                    angle = np.arctan2(drone.y-self.y,drone.x-self.x) 
                    curvec = ((drone.priority)**1)*np.array([np.cos(angle),np.sin(angle)])/np.linalg.norm((drone.x-self.x,drone.y-self.y))
                    tangential_vec = ((drone.priority)**1.5)*np.array([np.sin(angle),-np.cos(angle)])
                    vec += drone.v*(tangential_vec + curvec)/(self.priority)**1
        return vec

    def note_pos(self):
        self.file.write(str(self.x)+","+str(self.y)+"\n")

    def move(self, drones): 
        goal = self.goal
        #add the results obtained from avoid_collision and go_to_goal and publish them
        #also correct for yaw
        vec = self.go_to_goal(goal) - self.avoid_collision(drones)
        
        angle = np.arctan2(vec[1],vec[0]) - self.yaw
        
        norm = np.linalg.norm(vec)
        self.msg.linear.x = min(norm, self.v)*np.cos(angle)
        self.msg.linear.y = min(norm, self.v)*np.sin(angle)
        print(self.name,self.msg.linear.x,self.msg.linear.y)
        self.pub.publish(self.msg)

    def check_end(self):
        if self.msg.linear.x==0 and self.msg.linear.y==0 and self.check==True:
            self.time = (rospy.Time.now()-self.time).secs
            timefile.write(str(self.name+','+str(self.time)+','+str(self.priority)+'\n'))
            self.check=False
        
            


def take_off(drones):
    msg = Twist()
    msg.linear.z=1
    rate = rospy.Rate(10)
    for i in range(15):
        for drone in drones:
            drone.pub.publish(msg)
        rate.sleep()

    #tell it to stop now
    msg.linear.z=0
    for drone in drones:
        drone.pub.publish(msg)
    time.sleep(3)

drones = []
for i in range(15):
    drones.append(Uav(f'uav{i+1}', 3, 3,(i**2,i**2)))

    

if __name__ == '__main__':
    take_off(drones)
    for drone in drones:
        drone.time = rospy.Time.now()

    while True:
        for drone in drones:
            drone.move(drones)
            rate.sleep()
            drone.note_pos()
            drone.check_end()
        rate.sleep()   
    
    



        





