
//#include "Arduino.h"
#include "CustomDS.h"
#include "SerialReader.h"

#include "Wire.h"
#include "MPU6050_light_modified.h"
MPU6050 mpu1(Wire);


// 


//Sensor data


float gyrox1=(mpu1.getGyroX());
float gyroy1=(mpu1.getGyroY());
float gyroz1=(mpu1.getGyroZ());

float accelx1=(mpu1.getAccX());
float accely1=(mpu1.getAccY());
float accelz1=(mpu1.getAccZ());




  


// Out data buffer
::OutDataBuffer4Float outPayload;
