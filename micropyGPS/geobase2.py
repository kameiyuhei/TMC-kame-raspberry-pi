import os
import threading
import time
import serial
import micropyGPS
import subprocess
import pigpio
import bme280


from output1_csv import write_position
from acc import bmx055 #

pi = pigpio.pi()

#ポート番号の定義
Sw_pin = 23                         #変数"Sw_pin"に23を格納

pi.set_mode( Sw_pin, pigpio.INPUT )
pi.set_pull_up_down( Sw_pin, pigpio.PUD_DOWN)




BME280_ADDR = 0x76
I2C_CH = 1

sensor = bme280.bme280( pi, I2C_CH, BME280_ADDR )
sensor.setup()


###############　ここからGPS受信部分です　######################
gps = micropyGPS.MicropyGPS(9, 'dd')
# 出力のフォーマットは度数とする
gps.coord_format = 'dd'



def run_gps():
    """
    GPSモジュールを読み、GPSオブジェクトを更新する
    :return: None
    """
    # GPSモジュールを読み込む設定
#    s = serial.Serial('/dev/serial0', 115200, timeout=10)
    s = serial.Serial('/dev/serial0', 9600, timeout=10)

### 1Hzと同時にする高速通信化の前は('/dev/serial0', 9600, timeout=10)

    # 最初の1行は中途半端なデーターが読めることがあるので、捨てる
    s.readline()
    while True:
      # GPSデーターを読み、文字列に変換する
        sentence = s.readline().decode('utf-8')
      # 先頭が'$'でなければ捨てる
        if sentence[0] != '$':
            continue
      # 読んだ文字列を解析してGPSオブジェクトにデーターを追加、更新する
        for x in sentence:
            gps.update(x)
# 上の関数を実行するスレッドを生成
gps_thread = threading.Thread(target=run_gps, args=())
gps_thread.daemon = True
# スレッドを起動
gps_thread.start()
# 結果ファイル作成
output_dir = "./data"
os.makedirs(output_dir, exist_ok=True)

while True:
    # ちゃんとしたデーターがある程度たまったら出力する
    if gps.clean_sentences > 20:
        h = gps.timestamp[0] if gps.timestamp[0] < 24 else gps.timestamp[0] - 24
        acc = bmx055()
        ( temp, humi, press ) = sensor.get_value()

#######　受信したGPSデータの表示です　#######
        print(pi.read(Sw_pin))           #GPIO23が「ONで"1"」「OFFで"0"」
        print('%2d:%02d:%04.1f' % (h, gps.timestamp[1], gps.timestamp[2]))
        print('緯度経度: %2.8f, %2.8f' % (gps.latitude[0], gps.longitude[0]))
        print('海抜: %2.1f' % gps.altitude)
        print('方向: %2.2f' % gps.course)
        print('測位利用衛星: %s' % gps.satellites_used)
        print('■スピード: %2.1f' % gps.speed[2])
        print('acc  X_axis:',round(acc[0], 3), 'Y_axis:',round(acc[1], 3), 'Z_axis:',round(acc[2], 3)) #
        print ( "Temperature:", round( temp, 2 ) ,"C  Humidity:", round( humi, 2 ) ,"%  Pressure:", round( press, 2 ) , "hPa" )

###############　速度の扱い　#######
        lat = 0 # 変数定義
        long = 0 # 変数定義
        lat = gps.latitude[0]
        long = gps.longitude[0]
        Location = ("  ?  " )
        Allowed_speed_str = 110
        Allowed_speed = 10
        Vehicle_speed = gps.speed[2]
        loc = ('100 MAP無いです')###このあとMAPで照合ない場合表示されます
        switch = 0
        t = round( temp, 2 )
        hm = round( humi, 2 )
        p = round( press, 2 )

###### MAP照合するところ（ここをGoogleMapなどで作成します(平易なpanda化前の簡易記述です)
######　　↓表示 (前の数字は[許可速度]. スペース開け、[位置]です。
######　　　　　　（カンマ,ブランクのないワンワードで）)  ##########


        if  35.055649 < lat <= 35.055673 and 137.162670 < long <= 137.162713: # 位置範囲
            loc = ('20 Skid Pad')
            subprocess.call("aplay ./voice/Lane_change_se.wav", shell=True)
        if  35.054990 < lat <= 35.055056 and 137.163144 < long <= 137.163198: # 位置範囲
            loc = ('60 Enternce')
            subprocess.call("aplay ./voice/TCetr_headlight.wav", shell=True)
        if  35.051820 < lat <= 35.062341 and 137.150645  < long <= 137.169903: # 位置範囲
            loc = ('100 ToyotaTecCen')

####### Locを許可速度と位置に分けます  ##########
        Allowed_speed_str, Location = loc.split()
        Allowed_speed = int(Allowed_speed_str) #数値に変換

        print('■　許　可: %2.1f' % Allowed_speed)
        print('場所:',Location)
        print('')

####### 許可速度とと現在速度を比較します  ##########
        if  Allowed_speed < Vehicle_speed: # 判定
            print('< OVERSPEED! OVERSPEED! >')
        else:
            print(' 速度よし！')
        print('')

######### Log 作成です output_csv1.py要ります #######################
        # 時刻の変換
        time_str = (
                '20%02d/%02d/%02d %02d:%02d:%02d' %
                (   gps.date[2], gps.date[1], gps.date[0],
                    h, gps.timestamp[1], gps.timestamp[2]    )   )

        write_position(
            path="./data/log.csv",
            switch = pi.read(Sw_pin),
            rec_time=time_str,
            w_loc=loc,
            lat=gps.latitude[0],
            lon=gps.longitude[0],
            alt=gps.altitude,
            speed=gps.speed[2],
            course=gps.course,
            satellites_used=gps.satellites_used,
            x_acc = acc[0],
            y_acc = acc[1],
            z_acc = acc[2],
            t = round( temp, 2 ),
            hm = round( humi, 2 ),
            p = round( press, 2 ),)

########## 0.1秒に1回実行するように ##########
    time.sleep(0.1)
