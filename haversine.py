import sys, math
def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
if __name__ == "__main__":
    home_lat, home_lon = 39.9833, 116.3622
    name = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])
    d = hav(home_lat, home_lon, lat, lon)
    print(f"{name}: {d:.1f} km")
