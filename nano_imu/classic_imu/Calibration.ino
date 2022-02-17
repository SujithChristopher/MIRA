/*Calibration functions
void SetPredefinedCalib() {
//Calibrating Gyro
status = IMU.setGyroRange(MPU9250::GYRO_RANGE_250DPS);
status = IMU.calibrateGyro();
float gxb;
float gyb;
float gzb;
gxb = IMU.getGyroBiasX_rads();
gyb = IMU.getGyroBiasY_rads();
gzb = IMU.getGyroBiasZ_rads();
float gxb = 0.001; IMU.setGyroBiasX_rads(gxb);
float gyb = 0.001; IMU.setGyroBiasY_rads(gyb);
float gzb = 0.001; IMU.setGyroBiasZ_rads(gzb);
//Calibrating Accel
status = IMU.setAccelRange(MPU9250::ACCEL_RANGE_8G);
status = IMU.calibrateAccel();
float axb;
float ayb;
float azb;
float axs;
float ays;
float azs;
axb = IMU.getAccelBiasX_mss();
ayb = IMU.getAccelBiasY_mss();
azb = IMU.getAccelBiasZ_mss();
axs = IMU.getAccelScaleFactorX();
ays = IMU.getAccelScaleFactorY();
azs = IMU.getAccelScaleFactorZ();
float axb = 0.01; 
float axs = 0.97; 
IMU.setAccelCalX(axb,axs);
float ayb = 0.01; 
float ays = 0.97; 
IMU.setAccelCalY(ayb,ays);
float azb = 0.01; 
float azs = 0.97; 
IMU.setAccelCalZ(azb,azs);
//Calibrating Magneto
status = IMU.setDlpfBandwidth(MPU9250::DLPF_BANDWIDTH_20HZ);
status = IMU.calibrateMag();
float hxb;
float hxs;
float hyb;
hxb = IMU.getMagBiasX_uT();
hxs = IMU.getMagScaleFactorX();
hyb = IMU.getMagBiasY_uT();
hys = IMU.getMagScaleFactorY();
hzb = IMU.getMagBiasZ_uT();
hzs = IMU.getMagScaleFactorZ();
float hxb = 10.0; 
float hxs = 0.97; 
IMU.setMagCalX(hxb,hxs);
float hyb = 10.0; 
float hys = 0.97; 
IMU.setMagCalY(hyb,hys);
float hzb = 10.0; 
float hzs = 0.97; 
IMU.setMagCalZ(hzb,hzs);
}*/
