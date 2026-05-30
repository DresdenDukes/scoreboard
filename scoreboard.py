#!/usr/bin/env python3
import time, datetime
import math
import uvicorn
import toml
import json
import subprocess
import Adafruit_PCA9685
#from rpi_ws281x import PixelStrip, Color
from fastapi import FastAPI, BackgroundTasks, openapi
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

ADDR_H = 0x44
ADDR_G = 0x60
ADDR_O = 0x51
# pwm_home = Adafruit_PCA9685.PCA9685(address=ADDR_G, busnum=1)
# pwm_guest = Adafruit_PCA9685.PCA9685(address=ADDR_G, busnum=1)
# pwm_out = Adafruit_PCA9685.PCA9685(address=ADDR_O, busnum=1)
SERVO_OFF = 150
SERVO_ON = 600
SERVO_SLEEP = 0.5


global clockMode
clockMode = False

global state
state = {
    "home": 0,
    "guest": 0,
    "balls": 0,
    "strikes": 0,
    "out": 0,
}

def _getSegment(address):
    return Adafruit_PCA9685.PCA9685(address=address, busnum=1)


def getState():
    global state
    stateJson = json.dumps(state)
    return stateJson


def setHomeTenNumber(number: str) -> None:
    setNumber(number, ADDR_H, 7)

def setHomeNumber(number: str) -> None:
    setNumber(number, ADDR_H, 0)

def setGuestTenNumber(number: str) -> None:
    setNumber(number, ADDR_G, 7)

def setGuestNumber(number: str) -> None:
    setNumber(number, ADDR_G, 0)

def setNumber(number: str, address, offset: int) -> None:
    """display given number (or letter) on number segment
    """

    segment = _getSegment(address)
    numberValues = {
        "0": [1,2,3,4,5,6],
        "1": [2,3],
        "2": [1,2,4,5,7],
        "3": [1,2,3,4,7],
        "4": [2,3,6,7],
        "5": [1,3,4,6,7],
        "6": [1,3,4,5,6,7],
        "7": [1,2,3],
        "8": [1,2,3,4,5,6,7],
        "9": [1,2,3,4,6,7],
        "H": [2,3,5,6,7],
        "E": [1,4,5,6,7],
        "L": [4,5,6],
        "O": [1,2,3,4,5,6],
        "P": [1,2,5,6,7],
        "A": [1,2,3,5,6],
        "Y": [2,3,4,6,7],
        "B": [1,2,3,4,5,6,7],
    }
    pixels = numberValues.get(number, [])

    for x in range(1, 8):
        if number != "x" and x in pixels:
            onOff = SERVO_ON
        else:
            onOff = SERVO_OFF
        segment.set_pwm(x+offset, 0, onOff)
        time.sleep(SERVO_SLEEP)


def setBalls(balls: int):
    global state
    state["balls"] = balls

    segment = _getSegment(ADDR_O)
    if balls > 0:
        segment.set_pwm(1, 0, SERVO_ON)
        time.sleep(SERVO_SLEEP)
        if balls > 1:
            segment.set_pwm(2, 0, SERVO_ON)
            time.sleep(SERVO_SLEEP)
            if balls > 2:
                segment.set_pwm(3, 0, SERVO_ON)
                time.sleep(SERVO_SLEEP)
            else:
                segment.set_pwm(3, 0, SERVO_OFF)
                time.sleep(SERVO_SLEEP)
        else:
            segment.set_pwm(3, 0, SERVO_OFF)
            time.sleep(SERVO_SLEEP)
            segment.set_pwm(2, 0, SERVO_OFF)
            time.sleep(SERVO_SLEEP)
    else:
        segment.set_pwm(3, 0, SERVO_OFF)
        time.sleep(SERVO_SLEEP)
        segment.set_pwm(2, 0, SERVO_OFF)
        time.sleep(SERVO_SLEEP)
        segment.set_pwm(1, 0, SERVO_OFF)
        time.sleep(SERVO_SLEEP)


def setStrikes(strikes: int):
    global state
    state["strikes"] = strikes

    segment = _getSegment(ADDR_O)
    if strikes > 0:
        segment.set_pwm(4, 0, SERVO_ON)
        if strikes > 1:
            segment.set_pwm(5, 0, SERVO_ON)
        else:
            segment.set_pwm(5, 0, SERVO_OFF)
    else:
        segment.set_pwm(5, 0, SERVO_OFF)
        segment.set_pwm(4, 0, SERVO_OFF)


def setOuts(out: int):
    global state
    state["out"] = out

    segment = _getSegment(ADDR_O)
    if out > 0:
        segment.set_pwm(6, 0, SERVO_ON)
        time.sleep(SERVO_SLEEP)
        if out > 1:
            segment.set_pwm(7, 0, SERVO_ON)
            time.sleep(SERVO_SLEEP)
        else:
            segment.set_pwm(7, 0, SERVO_OFF)
            time.sleep(SERVO_SLEEP)
    else:
        segment.set_pwm(7, 0, SERVO_OFF)
        time.sleep(SERVO_SLEEP)
        segment.set_pwm(6, 0, SERVO_OFF)
        time.sleep(SERVO_SLEEP)


def clearBoard():
    # switch everything to OFF
    setOuts(0)
    setStrikes(0)
    setBalls(0)
    setHomeTenNumber("x")
    setHomeNumber("x")
    setGuestTenNumber("x")
    setGuestNumber("x")


def init(wait: int = 2):
    """display init sequence

    write "hello" and show loading bar below
    """
    clearBoard()

    setHomeTenNumber("H")
    setHomeNumber("I")
    time.sleep(wait)

    setBalls(1)
    time.sleep(wait)
    setBalls(2)
    time.sleep(wait)
    setBalls(3)
    time.sleep(wait)

    setStrikes(1)
    time.sleep(wait)
    setStrikes(2)
    time.sleep(wait)

    setOuts(1)
    time.sleep(wait)
    setOuts(2)
    time.sleep(wait*2)

    clearBoard()


def _getSingleNumbers(number) -> tuple[int, int]:
    one = number % 10
    ten = math.floor(number/10)
    return ten, one

def clockDisplay():
    """ display current time
    """
    now = datetime.datetime.now()
    hour = now.hour
    hourOne = hour % 10
    hourTen = math.floor(hour/10)
    minute = now.minute
    minuteOne = minute % 10
    minuteTen = math.floor(minute/10)

    setHomeTenNumber(str(hourTen))
    setHomeNumber(str(hourOne))
    setGuestTenNumber(str(minuteTen))
    setGuestNumber(str(minuteOne))

    time.sleep(5)


def clockLoop():
    global clockMode
    while clockMode:
        clockDisplay()


def setClock(hour: int, minute: int):
    if hour >= 0 and hour < 24 and minute >= 0 and minute < 60:
        command = f"sudo date --set {hour}:{minute}"
        subprocess.run(["sudo", "/usr/bin/date", "--set", f"{hour}:{minute}"])


if __name__ == '__main__':

    #init()

    data = toml.load("./pyproject.toml")
    scoreboardVersion = data["tool"]["poetry"]["version"]
    app = FastAPI(title="Scoreboard", version=scoreboardVersion, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    origins = [
        "http://172.17.17.1:7000",
        "http://172.17.17.1",
        "http://scoreboard",
        "http://localhost",
        "http://localhost:7000",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
    )

    @app.get("/set/inning/{count}", summary="set Inning", description="set Inning to given value", responses={})
    def inningapi(count: str):
        global clockMode
        clockMode = False
        # setInning(count)

    @app.get("/set/balls/{count}", summary="set Balls", description="set balls indicators to given value", responses={})
    def ballsapi(count: int):
        global clockMode
        clockMode = False
        setBalls(count)

    @app.get("/set/strikes/{count}", summary="set Strikes", description="set strike indicators to given value", responses={})
    def strikesapi(count: int):
        global clockMode
        clockMode = False
        setStrikes(count)

    @app.get("/set/outs/{count}", summary="set Outs", description="set out indicators to given value", responses={})
    def outsapi(count: int):
        global clockMode
        clockMode = False
        setOuts(count)


    @app.get("/set/home/{score}", summary="set home score", description="set Home score to given value", responses={})
    def homeapi(score: int):
        global clockMode
        global state
        state["home"] = score
        clockMode = False
        if score < 10:
            ten = "x"
            one = score
        else:
            ten, one = _getSingleNumbers(score)

        setHomeTenNumber(str(ten))
        setHomeNumber(str(one))


    @app.get("/set/guest/{score}", summary="set guest score", description="set Guest score to given value")
    def guestapi(score: int):
        global clockMode
        global state
        state["guest"] = score
        clockMode = False
        if score < 10:
            ten = "x"
            one = score
        else:
            ten, one = _getSingleNumbers(score)

        setGuestTenNumber(str(ten))
        setGuestNumber(str(one))


    @app.get("/clock", summary="show current time", description="use home and guest to display current time", responses={})
    def clockapi(background_tasks: BackgroundTasks):
        global clockMode
        if not clockMode:
            clockMode = True
            background_tasks.add_task(clockLoop)

    @app.get("/startgame", summary="set everything to 0", description="set digits, balls strikes and outs to zero and disable clock", responses={})
    def startgameapi(background_tasks: BackgroundTasks):
        global clockMode
        clockMode = False
        time.sleep(0.9)
        homeapi(0)
        guestapi(0)
        setBalls(0)
        setStrikes(0)
        setOuts(0)

    @app.get("/set/clock/{hour}/{minute}", summary="set time", description="set time")
    def clockapi(hour: int, minute: int):
        setClock(hour, minute)


    @app.get("/get/state", summary="get current state", description="get score and balls, strikes, out count")
    def getstateapi():
        return getState()


    @app.get("/", include_in_schema=False)
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
            clockDisplay()


    except KeyboardInterrupt:
        clearBoard()
        print("")
