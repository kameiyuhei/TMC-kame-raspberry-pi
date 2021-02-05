import csv

CorseOffSet = 0
def write_position(path, rec_time, w_loc, lat, lon, speed, course, aa, bb, x_acc, y_acc, z_acc):

    """
    csvに測位結果を書き込みます．
    :param path: 書き込み先
    :type path: str
    :param rec_time: 測位時刻 YYYYMMDD HH:mm:ss
    :type rec_time: str
    :param lat: 緯度 世界測地系 度数
    :type lat: float
    :param lon: 経度 世界測地系 度数
    :type lon: float
    :param alt: 海抜 メートル
    :type alt: float
    :param speed: スピード
    :type speed: float
    :param course: スピード
    :type course: float
    :param satellites_used: 測位衛星番号
    :type satellites_used: list
    """
    
    #################Log to MAP ################
#    lat_sn = lat - 0.00001
#    lat_en = lat + 0.00001
#    lon_sn = lon - 0.00001
#    lon_en = lon + 0.00001

# 衛星番号の整形
#    satellites_str = '-'.join([str(s) for s in satellites_used])

    # 書き込み
    with open(file=path, mode='a') as f:
        writer = csv.writer(f)
        writer.writerow(
            [rec_time, speed, w_loc, lat, lon, course, CorseOffSet, aa, bb, x_acc, y_acc, z_acc]
        )
