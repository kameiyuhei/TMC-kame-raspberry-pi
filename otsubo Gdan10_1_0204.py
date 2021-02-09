import os
import threading
import time
import serial
import micropyGPS
import pandas as pd
import pigpio
from kameioutput4_csv import write_position
from CoOfSt_Calc_t1 import CoOfSt, CoOfSt_Graph
from Force_idle import idle_on_relay
from Voice_manager import Sugg_spd_v, Over_spd_v, Drift_voice
#from acc_snsr import bmx055

pi = pigpio.pi()

Sw_pin = 23

pi.set_mode(Sw_pin, pigpio.INPUT)
pi.set_pull_up_down(Sw_pin, pigpio.PUD_DOWN)

switch = 0

gps_lon_o_for_pass = 0
gps_lat_o_for_pass = 0
time_str = 0
Vehicle_speed = 0
Allowed_speed = 0
slptime = 0

one_ply_s = 0
one_ply_crs = 0
one_ply_pls = 0
sound_invl_place = 0
sound_invl_s = 0
sound_invl_crs = 0

TC_Name = 'a'
#1TC_Lame='a'
TC_Renban ='a'
#1TC_Lane_old='a'
LatMap = 35.00001
LonMap = 137.00001
same_gpsdata = 0
gps_lat = 35.1196
gps_lon = 137.1102
gps_lat_old = 35.2
gps_lon_old = 137.2
DriftGraph = "□□□□□□□□□|□□□□□□□□□"
#緯度:latitude  経度:longtitude

#otsubo
lap_st_pos='a'
a_place_old='a'
lap_on=0
lap_off_count=0
lap_time=0.0
lap_time_m=0
lap_time_s=0
lap_time_ms=0
lap_time_old_m=0
lap_time_old_s=0
lap_time_old_ms=0
lap_st_time=time.time()


############## GPS/GNSS #######################
gps = micropyGPS.MicropyGPS(9, 'dd')
# 出力のフォーマットは度数とする
gps.coord_format = 'dd'
def run_gps():
    """
    GPSモジュールを読み、GPSオブジェクトを更新する
    :return: None
    """
    # GPSモジュールを読み込む設定
    s = serial.Serial('/dev/ttyACM0', 115200, timeout=10) #ichimil
#    s = serial.Serial('/dev/serial0', 115200, timeout=10) #akizuki UART
#    s = serial.Serial('/dev/ttyUSB0', 9600, timeout=10)
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
    # ちゃんとしたデーターがある程度たまった# 上の関数を実行するスレッドを生成
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
################## Platform #######################
        h = gps.timestamp[0] if gps.timestamp[0] < 24 else gps.timestamp[0] - 24
#        acc = bmx055()
        switch = pi.read(Sw_pin)
#        print('%2d:%02d:%04.1f' % (h, gps.timestamp[1], gps.timestamp[2]))
        gps_lon = gps.longitude[0]
        gps_lat = gps.latitude[0]
        gps_fix = gps.fix_stat
        Vehicle_speed = gps.speed[2] * 1.07 #Meter Error adjustment
        #Frequency adjustment #
        slptime = 1/((Vehicle_speed/3.6)+1)
        if slptime > 0.5:
            slptime = 0.5
# Pass if GPS was same 
        if gps_lon_o_for_pass == gps_lon and gps_lat_o_for_pass == gps_lat:
            same_gpsdata = 1
            gps_lon_o_for_pass = gps_lon
            gps_lat_o_for_pass = gps_lat

            continue

############ Mesh #### Special Thanks to maeda toshio 20200919  #########
        df = pd.read_csv('./data/shouhin_mstr500.csv')
        df = df.set_index('place')
        a = df[(df['lat_s'] <= gps_lat) & (df['lat_e'] > gps_lat) & (df['lon_s'] <= gps_lon) & (df['lon_e'] > gps_lon)]
        place = list(a.index)
        loc = place[0]
        
        
#        if same_gpsdata == 1:
#        if same_gpsdata == 0:
############### Map ##

        df = df.loc[place]  # 特定インデックスのデータを取得 => Series
        map_mesh = (df.iloc[0])            # 番号指定の場合は iloc を使う => Series
        # 先頭の 1 つのデータを取得
       ##https://maku77.github.io/python/numpy/dataframe-select.html
        place = place[0]
                
#################### Calc DriftDistance ########################
        LatMap = (float(map_mesh[0]) + 0.00001)
        LonMap = (float(map_mesh[2]) + 0.00001)
        CorseOffSet = CoOfSt(LatMap, LonMap, gps_lat, gps_lon, gps_lat_old, gps_lon_old)
        gps_lon_old = gps_lon
        gps_lat_old = gps_lat
        
        
#        CorseOffSet = 0.5
#   Pull Drift Graph ################
        DriftGraph = CoOfSt_Graph(CorseOffSet)

#   Drift Voice ################
        if one_ply_crs == 1:
            sound_invl_crs += 1
            if sound_invl_crs % 2 == 0: ##### 1秒を≒6周期で30は5秒くらい
                one_ply_crs = 0

        if one_ply_crs == 0 and Vehicle_speed > 10.0:
            one_ply_crs = 1
###            DG = Drift_voice(CorseOffSet)

#    for i in range (1:51):
#        if i % 3 == 0:

#   MAKE LOG ###############################
        if Vehicle_speed > 3:
            write_position(
                path="./data/log.csv",
                switch = pi.read(Sw_pin),
                rec_time=time_str, w_loc=loc, lon=gps.longitude[0], lat=gps.latitude[0],
                speed=gps.speed[2], course=gps.course, aa = CorseOffSet,bb = gps_fix)

#   Speedings ###########################
        Allowed_speed_str, a_place = loc.split() #許可速度と位置に分ける
        Allowed_speed = int(Allowed_speed_str) #数値に変換
        
#otsubo
        lap_st_pos='Mar_L_800'

        D_spd = 0 # 変数定義
        D_spd = Vehicle_speed - (Allowed_speed) #
        if  D_spd > 0: # 判定
            speed_st = '< OVERSPEED! >'

# Over Speed Announce
     
        if one_ply_s == 1:
            sound_invl_s += 1
            if sound_invl_s % 8 == 0: ##### 1秒を≒6周期で30は5秒くらい
                one_ply_s = 0
        if one_ply_s == 0:
            one_ply_s = 1
            OS = Over_spd_v(D_spd)  # Over Speed Announce

        speed_st = ' 速度よし！'

###################### Lane Change sound ###########################
#1            if 'Mar_' in a_place:
#1                TC_Name, TC_Lane, TC_Renbam = a_place.split("_") #分ける
#1                if  TC_Lane_old != TC_Lane:
#1                    subprocess.run("amixer sset Headphone 100%" , shell=True)
#1                    subprocess.Popen("aplay ./voice/Lane_change_se.wav", shell=True)
#1                TC_Lane_old = TC_Lane


#    Place Voice ###########################
        if one_ply_pls == 1:
            sound_invl_place += 1
            if sound_invl_place % 5 == 0: ##### 1秒を≒7周期で30は5秒くらい
                one_ply_pls = 0
        if one_ply_pls == 0 and Allowed_speed > 500:
                one_ply_pls = 1
                OS = Sugg_spd_v(Allowed_speed) # Suggested Speed Announce

# 時刻の変換
        time_str = ( '20%02d/%02d/%02d %02d:%02d:%02d' %
                (   gps.date[2], gps.date[1], gps.date[0],
                    h, gps.timestamp[1], gps.timestamp[2] ))
        
#otsubo lap_timer
        if a_place=='AICHI' or a_place=='GPS_suspended':
            if lap_off_count>0:
                lap_off_count=lap_off_count-1

        else:
            lap_off_count=10
        
        
        if lap_off_count==0:
            lap_on=0
            lap_time=0
            lap_time_m=0
            lap_time_s=0
            lap_time_ms=0
            
        else:
            if a_place==lap_st_pos and a_place_old!=lap_st_pos:   
                lap_time_old_m=lap_time_m
                lap_time_old_s=lap_time_s
                lap_time_old_ms=lap_time_ms
                lap_st_time=time.time()
                lap_on=1
            
        if lap_on==1:
            lap_time=time.time()-lap_st_time
            lap_time_m=int(lap_time//60)
            lap_time_s=int(lap_time % 60)
            lap_time_ms=int((lap_time-lap_time_m * 60 -lap_time_s)*100)
            
        a_place_old=a_place
        
####### Print #####################
        print('%2.7f, %2.7f' % (gps.latitude[0], gps.longitude[0])+"\n"
              +' 海抜 進行方向: %2.1f, %2.2f' % (gps.altitude, gps.course)+"\n"
              +' ■　許 可 : %2.1f' % Allowed_speed + '         '+"\n"
              +' ■スピード: %2.1f' % gps.speed[2] + '      '+"\n"
#              +' ■ X_ACC : %f' % acc[0] + '      '+"\n"
#              +' ■ Y_ACC : %f' % acc[1] + '      '+"\n"
#              +' ■ Z_ACC : %f' % acc[2] + '      '+"\n"
              +' ■  場 所 :',a_place + '         '+"\n"
              +' ■ジャッジ:',speed_st + '      '+"\n"
              +' ■Drift:',DriftGraph + "\n"
              +' ■Drift:',DriftGraph + "\n"
              +' ■Drift: %d' % switch + '         '+"\n"
              +' ■ｺｰｽズレ : %2.2f' % CorseOffSet + '        '+"\n"#+"\033[9A",end="")
              +'otsubo moni:',a_place_old + '        '+"\n"
              +' ■Lap_Time:'+str(lap_time_m).zfill(2)+':'+str(lap_time_s).zfill(2)
              +'.'+str(lap_time_ms).zfill(2)+'    ■Lap_Time_OLD:'+str(lap_time_old_m).zfill(2)
              +':'+str(lap_time_old_s).zfill(2)+'.'+str(lap_time_old_ms).zfill(2)
              +"\033[11A",end="")
# 1mに1回実行するように

# 1mに1回実行するように
    time.sleep(slptime)
#    time.sleep(0.1)
