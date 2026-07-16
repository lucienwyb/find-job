import math
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat/2)**2 + math.cos(rlat1)*math.cos(rlat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

if __name__ == "__main__":
    import sys
    # 北医三院 39.9833, 116.3622
    home = (39.9833, 116.3622)
    pts = [
        ("爱立信-利泽中园", 39.9930, 116.4700),
        ("诺基亚-亦庄", 39.8000, 116.5200),
        ("施耐德-望京", 39.9920, 116.4700),
        ("ABB-酒仙桥", 39.9700, 116.4900),
        ("西门子-望京", 39.9920, 116.4700),
        ("博世-朝阳", 39.9200, 116.4500),
        ("大陆-朝阳", 39.9100, 116.4600),
        ("电装-朝阳", 39.9200, 116.4600),
        ("戴尔-中关村", 39.9800, 116.3200),
    ]
    for name, lat, lon in pts:
        d = haversine_km(home[0], home[1], lat, lon)
        print(f"{name}: {d:.2f} km")
