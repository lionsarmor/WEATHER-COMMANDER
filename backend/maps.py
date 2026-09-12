"""Native north-up Philippine geography shared by National and Radar views."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
GEO=Path(__file__).resolve().parents[1]/'assets/data/philippines.geojson'

def project(lon,lat):
 return round(142+(lon-121.2)*15),round(12+(19.5-lat)*15.4)

def philippines():
 # Only terrain indices: no color from radar.LEVELS can imply rain here.
 picture=Image.new('P',(336,224),2);draw=ImageDraw.Draw(picture)
 for y in range(1,224,2):draw.line((0,y,335,y),fill=3)
 geo=json.loads(GEO.read_text())['geometry']
 polygons=geo['coordinates'] if geo['type']=='MultiPolygon' else [geo['coordinates']]
 for polygon in polygons:
  for i,ring in enumerate(polygon):
   points=[project(*point[:2]) for point in ring]
   draw.polygon(points,fill=7 if i==0 else 2)
   if i==0:draw.line(points,fill=9,width=1)
 for y in range(1,224,2):
  for x in range(336):
   if picture.getpixel((x,y))==7:picture.putpixel((x,y),14)
 return picture
