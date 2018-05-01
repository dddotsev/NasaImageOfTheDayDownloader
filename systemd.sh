#!/bin/sh

start() {
    exec python main.py 2>&1 >>log.log
}

stop() {
}

case $1 in
  start|stop) "$1" ;;
esac
