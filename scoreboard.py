#!/usr/bin/env python3
import time, datetime
import math
import uvicorn
import toml
from rpi_ws281x import PixelStrip, Color
from fastapi import FastAPI, BackgroundTasks, openapi
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

# LED strip configuration:
LED_COUNT = 150       # Number of LED pixels.
LED_PIN = 10          # GPIO pin connected to the pixels (18 uses PWM - 10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


GUEST_TEN_OFFSET = 60
GUEST_ONE_OFFSET = 37
HOME_ONE_OFFSET = 83
HOME_TEN_OFFSET = 106
INNING_OFFSET = 129
CLOCK_SECONDS_DOT = INNING_OFFSET + 10

BALLS_OFFSET = 12
STRIKES_OFFSET = 22
OUT_OFFSET = 32

# default color
DEF_R = 0
DEF_G = 255
DEF_B = 0


global clockMode
clockMode = False


def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def setInning(strip: PixelStrip, color: Color, number: str, offset: int) -> None:
    """display given number (or letter) on innnig segment

    offset: (int) how many pixel before this segment
    """
    inningValues = {
        "0": [1,2,3,4,5,6,8,9,11,12,13,14],
        "1": [5,6,8,9],
        "2": [3,4,5,6,11,12,13,14,15,16],
        "3": [3,4,5,6,8,9,11,12,15,16],
        "4": [1,2,5,6,8,9,15,16],
        "5": [1,2,3,4,8,9,11,12,15,16],
        "6": [1,2,3,4,8,9,11,12,13,14,15,16],
        "7": [3,4,5,6,8,9,10],
        "8": [1,2,3,4,5,6,8,9,11,12,13,14,15,16],
        "9": [1,2,3,4,5,6,8,9,11,12,15,16],
        "L": [1,2,11,12,13,14],
    }
    pixels = inningValues.get(number, [])

    # clear segment
    for i in range(1, 17):
        strip.setPixelColor(i+offset, Color(0,0,0))
    # set new value
    for i in pixels:
        strip.setPixelColor(i+offset, color)
    strip.show()

def setNumber(strip: PixelStrip, color: Color, number: str, offset: int) -> None:
    """display given number (or letter) on number segment

    offset: (int) how many pixel before this segment
    """
    numberValues = {
        "0": [1,2,3,5,6,7,8,9,10,11,12,13,15,16,17,21,22,23],
        "1": [1,2,3,5,6,7],
        "2": [5,6,7,8,9,10,15,16,17,18,19,20,21,22,23],
        "3": [1,2,3,5,6,7,8,9,10,18,19,20,21,22,23],
        "4": [1,2,3,5,6,7,11,12,13,18,19,20],
        "5": [1,2,3,8,9,10,11,12,13,18,19,20,21,22,23],
        "6": [1,2,3,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23],
        "7": [1,2,3,5,6,7,8,9,10],
        "8": [1,2,3,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23],
        "9": [1,2,3,5,6,7,8,9,10,11,12,13,18,19,20,21,22,23],
        "H": [1,2,3,5,6,7,11,12,13,15,16,17,18,19,20],
        "E": [8,9,10,11,12,13,15,16,17,18,19,20,21,22,23],
        "L": [11,12,13,15,16,17,21,22,23],
        "O": [1,2,3,5,6,7,8,9,10,11,12,13,15,16,17,21,22,23],
    }
    pixels = numberValues.get(number, [])

    # clear segment
    for i in range(1, 24):
        strip.setPixelColor(i+offset, Color(0,0,0))
    # set new value
    for i in pixels:
        fixedPixel = i+offset
        if offset == HOME_TEN_OFFSET and i>14:
            # one pixel missing 
            fixedPixel = fixedPixel-1
        strip.setPixelColor(fixedPixel, color)
    strip.show()


def setBalls(balls: int, stripe: PixelStrip):
    setLineDots(balls, stripe, Color(0,255,0), BALLS_OFFSET)

def setStrikes(strikes: int, stripe: PixelStrip):
    setLineDots(strikes, stripe, Color(255,0,0), STRIKES_OFFSET)

def setOuts(out: int, stripe: PixelStrip):
    setLineDots(out, stripe, Color(255,0,20), OUT_OFFSET)


def setLineDots(count: int, stripe: PixelStrip, color: Color, offset: int):
    """set balls
    
    balls: allowed values: 0, 1, 2, 3
    """
    off = Color(0,0,0)

    strip.setPixelColor(offset, off)
    strip.setPixelColor(offset+2, off)
    strip.setPixelColor(offset+4, off)

    if count > 0:
        strip.setPixelColor(offset, color)

    if count > 1:
        strip.setPixelColor(offset+2, color)

    if count > 2:
        strip.setPixelColor(offset+4, color)

    strip.show()


def clearBoard(strip: PixelStrip):
    """turn off all pixels"""
    colorWipe(strip, Color(0, 0, 0), 0)


def init(strip: PixelStrip, color: Color, wait: int = 2):
    """display init sequence

    write "hello" and show loading bar below
    """
    clearBoard(strip)

    setNumber(strip, color, "H", HOME_TEN_OFFSET)
    setNumber(strip, color, "E", HOME_ONE_OFFSET)
    setInning(strip, color, "L", INNING_OFFSET)
    setNumber(strip, color, "L", GUEST_TEN_OFFSET)
    setNumber(strip, color, "O", GUEST_ONE_OFFSET)
    time.sleep(wait)

    setBalls(1, strip)
    time.sleep(wait)
    setBalls(2, strip)
    time.sleep(wait)
    setBalls(3, strip)
    time.sleep(wait)

    setStrikes(1, strip)
    time.sleep(wait)
    setStrikes(2, strip)
    time.sleep(wait)

    setOuts(1, strip)
    time.sleep(wait)
    setOuts(2, strip)
    time.sleep(wait)

    clearBoard(strip)


def _getSingleNumbers(number) -> tuple[int, int]:
    one = number % 10
    ten = math.floor(number/10)
    return ten, one

def clockDisplay(strip: PixelStrip, color: Color):
    """ display current time and blink seconds dot (once)
    """
    now = datetime.datetime.now()
    hour = now.hour
    hourOne = hour % 10
    hourTen = math.floor(hour/10)
    minute = now.minute
    minuteOne = minute % 10
    minuteTen = math.floor(minute/10)

    setNumber(strip, color, str(hourTen), HOME_TEN_OFFSET)
    setNumber(strip, color, str(hourOne), HOME_ONE_OFFSET)
    setNumber(strip, color, str(minuteTen), GUEST_TEN_OFFSET)
    setNumber(strip, color, str(minuteOne), GUEST_ONE_OFFSET)

    # blink seconds dot
    strip.setPixelColor(CLOCK_SECONDS_DOT, color)
    strip.show()
    time.sleep(0.05)
    strip.setPixelColor(CLOCK_SECONDS_DOT, Color(0, 0, 0))
    strip.show()
    time.sleep(0.95)


def clockLoop(strip: PixelStrip):
    global clockMode
    while clockMode:
        clockDisplay(strip, defaultColor)
    else:
        setNumber(strip, defaultColor, "x", HOME_TEN_OFFSET)
        setNumber(strip, defaultColor, "x", HOME_ONE_OFFSET)
        setNumber(strip, defaultColor, "x", GUEST_TEN_OFFSET)
        setNumber(strip, defaultColor, "x", GUEST_ONE_OFFSET)
        strip.setPixelColor(CLOCK_SECONDS_DOT, Color(0, 0, 0))
        strip.show()


if __name__ == '__main__':

    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    defaultColor = Color(DEF_R, DEF_G, DEF_B)

    init(strip, defaultColor)

    data = toml.load("./pyproject.toml")
    scoreboardVersion = data["tool"]["poetry"]["version"]
    app = FastAPI(title="Scoreboard", version=scoreboardVersion, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/set/inning/{count}", summary="set Inning", description="set Inning to given value", responses={})
    def inningapi(count: str):
        global clockMode
        clockMode = False
        setInning(strip, defaultColor, count, INNING_OFFSET)

    @app.get("/set/balls/{count}", summary="set Balls", description="set balls indicators to given value", responses={})
    def ballsapi(count: int):
        global clockMode
        clockMode = False
        setBalls(count, strip)

    @app.get("/set/strikes/{count}", summary="set Strikes", description="set strike indicators to given value", responses={})
    def strikesapi(count: int):
        global clockMode
        clockMode = False
        setStrikes(count, strip)

    @app.get("/set/outs/{count}", summary="set Outs", description="set out indicators to given value", responses={})
    def outsapi(count: int):
        global clockMode
        clockMode = False
        setOuts(count, strip)


    @app.get("/set/home/{score}", summary="set home score", description="set Home score to given value", responses={})
    def homeapi(score: int):
        global clockMode
        clockMode = False
        if score < 10:
            ten = "x"
            one = score
        else:
            ten, one = _getSingleNumbers(score)

        setNumber(strip, defaultColor, str(ten), HOME_TEN_OFFSET)
        setNumber(strip, defaultColor, str(one), HOME_ONE_OFFSET)


    @app.get("/set/guest/{score}", summary="set guest score", description="set Guest score to given value")
    def guestapi(score: int):
        global clockMode
        clockMode = False
        if score < 10:
            ten = "x"
            one = score
        else:
            ten, one = _getSingleNumbers(score)
        setNumber(strip, defaultColor, str(ten), GUEST_TEN_OFFSET)
        setNumber(strip, defaultColor, str(one), GUEST_ONE_OFFSET)

    @app.get("/clock", summary="show current time", description="use home and guest to display current time", responses={})
    def clockapi(background_tasks: BackgroundTasks):
        setInning(strip, defaultColor, "x", INNING_OFFSET)
        global clockMode
        if not clockMode:
            clockMode = True
            background_tasks.add_task(clockLoop, strip)

    @app.get("/startgame", summary="set everything to 0", description="set digits, balls strikes and outs to zero and disable clock", responses={})
    def startgameapi(background_tasks: BackgroundTasks):
        setInning(strip, defaultColor, "0", INNING_OFFSET)
        global clockMode
        clockMode = False
        time.sleep(0.9)
        homeapi(0)
        guestapi(0)
        setBalls(0, strip)
        setStrikes(0, strip)
        setOuts(0, strip)


    @app.get("/")
    def defaultpage():
        return "see /docs"

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()


    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )

    def custom_openapi():
        """hide responses"""
        if not app.openapi_schema:
            app.openapi_schema = openapi.utils.get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )
            for _, method_item in app.openapi_schema.get('paths').items():
                for _, param in method_item.items():
                    responses = param.get('responses')
                    # remove 422 response, also can remove other status code
                    if '422' in responses:
                        del responses['422']
                    if '200' in responses:
                        del responses['200']
        return app.openapi_schema

    app.openapi = custom_openapi


    uvicorn.run(app, host="0.0.0.0", port=7000)

    try:
        while True:
            clockDisplay(strip, defaultColor)
            # for i in tenpixels:
            #     strip.setPixelColor(i, Color(0, 5, 0))
            #     #strip.setBrightness(55)
            # strip.show()
            # time.sleep(1)
            # for i in tenpixels:
            #     strip.setPixelColor(i, Color(0, 55, 0))
            #     #time.sleep(2)
            #     #strip.setBrightness(5)
            # strip.show()
            # time.sleep(1)

    #         #print('Color wipe animations.')
    #         colorWipe(strip, Color(255, 0, 0), 0)  # Red wipe
    #         colorWipe(strip, Color(0, 255, 0), 0)  # Green wipe
    #         # colorWipe(strip, Color(0, 0, 255))  # Blue wipe

    except KeyboardInterrupt:
        clearBoard(strip)
        print("")
