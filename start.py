import time
import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont,ImageChops,ImageFilter
from adafruit_rgb_display import st7789
import asyncio


# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
height = disp.width  # we swap height/width to rotate it to landscape!
width = disp.height
draw_image = Image.new("RGBA", (width, height))
rotation = 90

# Get drawing object to draw on image.
draw = ImageDraw.Draw(draw_image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0, 0))
disp.image(draw_image, rotation)
# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)

# Turn on the backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

buttonA = digitalio.DigitalInOut(board.D23)
buttonB = digitalio.DigitalInOut(board.D24)
buttonA.switch_to_input()
buttonB.switch_to_input()    

time_to_start = 185
time_running = False
update_tv = False
display_horn = False

def make_horn_brighter(im):
    s = im.split()
    R, G, B, A = 0, 1, 2, 3
    # mask = s[A].point(lambda i: i>100 and 255)
    # out = s[G].point(lambda i: i+80)
    # s[G].paste(out,None,mask)
    s[B].paste(s[A]) 
    s[R].paste(s[A]) 
    im = Image.merge(im.mode,s)
    return im
    
    # Draw a black filled box to clear the image.
    # draw.rectangle((0, 0, width, height), outline=0, fill="#808080")
    
# def printt(m)
#     print(f'{time.perf_counter_ns()/1000000)}

async def long():
    # turn on output
    print('long ON')
    await asyncio.sleep(1)
    print('long OFF')
    # turn off output
async def short():
    # turn on output
    print('short ON')
    await asyncio.sleep(0.3)
    print('short OFF')
    # turn off output
    
horn_pattern = dict()
horn_pattern[180] = [long,long,long]
horn_pattern[120] = [long,long]
horn_pattern[90] = [long,short,short,short]
horn_pattern[60] = [long]
horn_pattern[30] = [short,short,short]
horn_pattern[20] = [short,short]
horn_pattern[10] = [short]
horn_pattern[5] = [short]
horn_pattern[4] = [short]
horn_pattern[3] = [short]
horn_pattern[2] = [short]
horn_pattern[1] = [short]
horn_pattern[0] = [long]

async def update_time():
    global time_running
    global time_to_start
    print('start update_time')
    while True:
        await asyncio.sleep(1)
        # print('utr', time_running)
        if time_running:
            print(f'update_time {time_to_start=}')
            time_to_start = time_to_start - 1
            update_time_image = True        
        
async def update_time_image():
    global draw_image
    global update_tv
    print('start update_time_image')
    displayed_time = -1
    background = Image.open("sailstart.JPG").resize((240,135),Image.LANCZOS)
    tv_box = (0,0,240,135)
    while True:
        await asyncio.sleep(0.05)
        if displayed_time != time_to_start:
            # print(f"update_time_image {time_to_start=}")  
            print("start updatetime", time.perf_counter_ns()/1000000)         
            displayed_time = time_to_start
            draw_image = background.crop(tv_box)
            # draw_image = Image.open("sailstart.JPG").resize((240,135))
            # print("mid   updatetime", time.perf_counter_ns()/1000000)
            y = top
            ImageDraw.Draw(draw_image).text((x,y), f"{abs(time_to_start)//60}:{abs(time_to_start)%60:02}", font=font, fill=( "#80FF80" if time_to_start<0 else "#FF00FF"))
            update_tv = True
            print("end   updatetime", time.perf_counter_ns()/1000000)

async def write_to_tv():
    global update_tv
    global draw_image
    global display_horn
    print('start write_to_tv')
    horn_image = Image.open("horn5.png").resize((60,60))
    horn_image = make_horn_brighter(horn_image)
    horn_box = (170,0,230,60)
    tv_box = (0,0,240,135)
    while True:
        await asyncio.sleep(0.01)
        if update_tv:
            print("start draw", time.perf_counter_ns()/1000000)
            display_image = draw_image.crop(tv_box)
            update_tv = False
            # print('write_to_tv')
            if display_horn:
                display_image.paste(horn_image,horn_box,horn_image)
            # print("start disp", time.perf_counter_ns()/1000000)
            # bob = display_image.rotate(90)
            # print(display_image,bob)
            # print("mid draw  ", time.perf_counter_ns()/1000000)
            disp.image(display_image, rotation)
            print("end draw  ", time.perf_counter_ns()/1000000)
            
async def horn():
    global time_to_start
    global display_horn
    global horn_pattern
    global update_tv
    print('start horn')
    horn_q = []
    last_processed_time = 0
    post_beep_wait = 0.5
    while True:
        await asyncio.sleep(0.01)
        if last_processed_time != time_to_start:
            last_processed_time = time_to_start
            horn_q = horn_pattern.get(time_to_start,[])
            for beep in horn_q:
                display_horn = True
                update_tv = True
                # turn on horn output
                await beep()
                display_horn = False
                update_tv = True
                await asyncio.sleep(post_beep_wait)

async def ui():
    global time_running
    global time_to_start
    print('start ui')
    time_to_start = 15
    time_running = False
    backlight_state = True
    
    while(1):
        await asyncio.sleep(0.1)
        if time_running:
            if (buttonA.value==0) and (buttonB.value==0):
                time_to_start = 185
                time_running = False
                print(f'{time_running=}')
                await asyncio.sleep(2) # just so it doesn't immediately look for start
            elif (buttonA.value==0) or (buttonB.value==0):
                backlight_state = not backlight_state
                backlight.value = backlight_state
                await asyncio.sleep(1) # just so it doesn't immediately look for start
        else:
            if (buttonA.value==0) or (buttonA.value==0):
                time_running = True
                print(f'{time_running=}')
                await asyncio.sleep(1)

async def main():
    print('start main')
    # global time_to_start
    # global time_running
    
    # init_tv()
    # init_background()
    await asyncio.gather(ui(),
                         horn(),
                         write_to_tv(),
                         update_time_image(),
                         update_time())

    

        
    



if __name__ == "__main__":
    asyncio.run(main())