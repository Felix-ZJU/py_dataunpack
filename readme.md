# py_dataunpack

this tool unpack structured binary data file as comma-separated text file (csv file) accoridng to the format defined in json config file.

the binary data file may be a microcontroller log, or a record of serial port messages.

the structure information of the binary data file needs to be specified in a json config file. only fixed length structures are supported for the moment.

## how to use

the tool needs two arguments. The first argument is the path to the data file, and the second one the json config file:

    $ py_dataunpack.py path_of_data_file/data_file.dat path_of_config/config.json

if the above command is successfully executed, the data is unpacked into `path_of_data_file/data_file.csv` (or **overwritten** if the file already exists).

the second argument is optional. if it is not provided, the tool looks for:

1. json file with the same file name as the data file, and
2. a default json file named defconfig.json.

for example when the following command executed:

    $ py_dataunpack.py path_of_data_file/data_file.dat

the tool first looks for `path_of_data_file/data_file.json` (not `path_of_data_file/data_file.dat.json`), and then `path_of_data_file/defconfig.json`.

## the json config file

the json file describes the data file structure (also known as a frame or a message). it contents the following elements:

* `frame_size`
  the length of the structure, in byte.

* `header_size` and `header_hex`
  the header of the structure. `header_size` is the length of the header in byte, and `header_hex` the hexadecimal string of the header. the header information is used to search for the beginning of a structure (note that the begining of data file may not be the begining of a structure).

* `counter_size` and `counter_offset`
  the counter in the structure, optional. `counter_size` is the length of the counter in byte, 0 if there is no counter. `counter_offset` is the start location of the counter in one frame. when the counter information is provided, it is used as well to search for the beginning of a structure.

* `payload_size` and `payload_offset`
  the payload length and offset in the structure, used to be unpacked. the payload may content header or counter when needed, or may be a part of the actural payload.

* `content`
  an array of property sets describes each element in payload (or column in csv file).
  The properties in content:

  - `title`: title (name) of the element.
  - `derived`: optional, 0 or 1, whether the element is derived from other elements.
  - `offset`: offset of the element in payload. this property is not needed when `derived` is defined and equals to 1.
  - `s_fmt`: how to unpack the binary of the element from payload. refer to the python struct.unpack format. this property is not needed when `derived` is defined and equals to 1.
  - `hidden`: optional, 0 or 1, whether the element is to be written to the .csv output file.
  - `p_fmt`: how to export the element to the .csv output file. refer to the string format.
  - `lambda`: how to convert the value from struct.unpack to the desired value to export.
  - `lambda_ref`: when value from other elements are required, the other element index can be put here.

## an example

### cap-udata-adc&imu-20190622_2225

the data file is captured from serial port. the structure of the data file is defined in C language as follow (`uart_data_t`), it contents a header, a record number counter, an array of ADC values and a sub-structure of IMU (MPU6050) data.

	#include <stdint.h>
	
	typedef struct _mpu6000_accel_t
	{
	  uint16_t ax;
	  uint16_t ay;
	  uint16_t az;
	} mpu6000_accel_t;
	
	typedef uint16_t mpu6000_temp_t;
	
	typedef struct _mpu6000_gyro_t
	{
	  uint16_t gx;
	  uint16_t gy;
	  uint16_t gz;
	} mpu6000_gyro_t;
	
	typedef struct
	{
	  mpu6000_accel_t acce;
	  mpu6000_temp_t  temp;
	  mpu6000_gyro_t  gyro;
	} mpu6000_data_t;
	
	#define UART_DATA_ADC_NUM 5
	
	typedef struct
	{
	  uint8_t        hdr; // 0xFE
	  uint8_t        cnt; // up-counter
	  int16_t        adc[UART_DATA_ADC_NUM];
	  mpu6000_data_t imu;
	} uart_data_t;

the json file is as follow:

	{
	  "frame_size"     : 26,
	  "header_size"    : 1,
	  "header_hex"     : "FE",
	  "counter_size"   : 1,
	  "counter_offset" : 1,
	  "payload_size"   : 24,
	  "payload_offset" : 2,
	  "content" :
	  [
	    {"title":"vref_raw", "offset": 8, "s_fmt":"h", "hidden":1},
	    {"title":"vsup",     "offset": 0, "s_fmt":"h", "p_fmt":"%.2f", "lambda":"lambda x:11.0*1.205*x[0]/x[1]", "lambda_ref":[0]},
	    {"title":"vsensor",  "offset": 6, "s_fmt":"h", "p_fmt":"%.4f", "lambda":"lambda x:1.205/0.15*x[0]/x[1]", "lambda_ref":[0]},
	    {"title":"ax",       "offset":10, "s_fmt":"h", "p_fmt":"%.4f", "lambda":"lambda x:x*8.0/32768"},
	    {"title":"az",       "offset":14, "s_fmt":"h", "p_fmt":"%.4f", "lambda":"lambda x:x*8.0/32768"},
	    {"title":"gy",       "offset":20, "s_fmt":"h", "p_fmt":"%.4f", "lambda":"lambda x:x*2000.0/32768"},
	    {"title":"temp",     "offset":16, "s_fmt":"h", "p_fmt":"%.2f", "lambda":"lambda x:36.53+x/340.0"}
	  ]
	}

* line 2: `"frame_size" : 26,`, the total size of one frame is 26 bytes.

* line 3 and line 4: `"header_size" : 1,`, `"header_hex" : "FE",`, tells that the header of the structure is one byte `0xFE`.

* line 5 and line 6: `"counter_size" : 1,`, `"counter_offset" : 1,`, tells that a counter is at the second byte, the length of the counter is 8 bit (one byte).

* line 7 and line 8: `"payload_size" : 24,`, `"payload_offset" : 2,`, specifies the payload, which starts at byte offset 2 and the length is 24 bytes.

* line 11: the element, `vref_raw`, is the reference voltage of the adc values. it is located at offset 8, is a int16_t signed integer (struct.unpack format `h`), is not exported to the .csv file (`"hidden"` property defined).

* line 12: the element, `vsup`, is the supply voltage of the device. it is located at offset 0 of the payload, is a int16_t signed integer, and exported as a float number with 2 decimal places (`"p_fmt":"%.2f"`). it reference the first element `vref_raw` (`"lambda_ref":[0]`), and the output value is calculated according to the lambda function `lambda x:11.0*1.205*x[0]/x[1]`, means that `vsup = 11.0*1.205*vsup_raw / vref_raw`, where vsup_raw is the int16_t value unpacked from data file.

* line 17: the element, `temp`, is the temperature data measured by the IMU. its offset is 16, output as a float with 2 decimal places, and calculated according to a lambda function `lambda x:36.53+x/340.0` that convert the int16_t data to a float value.
