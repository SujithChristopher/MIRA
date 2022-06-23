// to communicate between I2C devices

#include "variable.h"
#include "Arduino.h"
#include "CustomDS.h"

long timer = 0;

void setup()
{

  Serial1.begin(115200);


  //Initiate the Wire library and join the I2C bus as a master or slave. This should normally be called only once.
  Wire.begin();


  mpu1.begin(1, 0);
  mpu1.calcOffsets(true, true);
  mpu1.setFilterGyroCoef(0.98);

}
void loop() {

  mpu1.update();

  gyrox1 = (mpu1.getGyroX());
  gyroy1 = (mpu1.getGyroY());
  gyroz1 = (mpu1.getGyroZ());
  accelx1 = (mpu1.getAccX());
  accely1 = (mpu1.getAccY());
  accelz1 = (mpu1.getAccZ());

  writeSensorStream();

  //Check Data Communication tab for function
  //delay(15);

}
