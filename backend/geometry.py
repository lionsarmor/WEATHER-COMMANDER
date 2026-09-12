"""Spherical Albers geometry matching the dashboard's us-atlas national map."""
import math
N=(math.sin(math.radians(29.5))+math.sin(math.radians(45.5)))/2
C=math.cos(math.radians(29.5))**2+2*N*math.sin(math.radians(29.5))

def project(lon,lat):
 rho=math.sqrt(C-2*N*math.sin(math.radians(lat)))/N
 theta=N*math.radians(lon+96)
 return rho*math.sin(theta),rho*math.cos(theta)

def unproject(x,y):
 rho=math.hypot(x,y)
 return math.degrees(math.atan2(x,y)/N)-96,math.degrees(math.asin((C-(rho*N)**2)/(2*N)))

# Derived from contiguous state geometry; no runtime geodata download is needed.
BOUNDS=(-0.3688841452039383, 1.0574495154321397, 0.3531117886546076, 1.5140685816350008)

def pixel(lon,lat):
 x,y=project(lon,lat);x0,y0,x1,y1=BOUNDS
 return 6+(x-x0)/(x1-x0)*324,2+(y-y0)/(y1-y0)*206

def coordinate(x,y):
 x0,y0,x1,y1=BOUNDS
 return unproject(x0+(x-6)/324*(x1-x0),y0+(y-2)/206*(y1-y0))
