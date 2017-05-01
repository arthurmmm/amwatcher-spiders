#! /bin/bash

# VAR
IMAGE="daocloud.io/arthurmmm/amwatcher-spiders"
CONTAINER="amwatcher-spider-dev"
CONFIG_SRC="/data/amwatcher_spider/amwatcher-spider.yml"
CONFIG="/etc/amwatcher-spider.yml"
CONFIG_TEST_SRC="/data/amwatcher_spider/amwatcher-spider.test.yml"
CONFIG_TEST="/etc/amwatcher-spider.test.yml"

# FUNCTIONS
function help() {
    echo 'Usage: '
    echo './devcli.sh [start|stop|run|tunnel|shell|rmc|rmi|trim]'
    exit 0
}

function tunnel() {
    echo 'Start SSH Tunnel to Databases...'
    echo 'Connecting MongoDB...'
    ssh -NfL 27017:10.66.200.252:27017 qcloud-sh
    echo 'Connecting Redis'
    ssh -NfL 6379:10.66.114.52:6379 qcloud-sh
}

function loop() {
    echo 'Looping, hit [CTRL+C] to stop...' > /var/tmp/loop.msg
    tail -f /var/tmp/loop.msg
}

function build_container() {
    # Pull DEV docker image from Daocloud
    if docker inspect $IMAGE > /dev/null 2>&1;
    then
        echo 'Image already exist, skip pulling...'
    else
        echo 'Login Daocloud:'
        docker login daocloud.io
        docker pull $IMAGE
    fi

    # You need build config file into /data/amwatcher_spider first!
    # Run DEV docker in background, with no task started
    if docker inspect $CONTAINER > /dev/null 2>&1;
    then
        echo 'Container already exist, skip building...'
        docker start $CONTAINER
    else
        echo 'Building container...'
        docker run -d \
            -v /data:/data:rw \
            -v $CONFIG_TEST_SRC:$CONFIG_TEST:ro \
            -v $CONFIG_SRC:$CONFIG:ro \
            -v `echo ~/.ssh`:/root/.ssh:ro \
            -v `pwd`:/usr/src/app:ro \
            --name $CONTAINER $IMAGE \
            ./devcli.sh tunnel
    fi
}

function run_test() {
    # Running testing on docker container
    if docker exec amwatcher-spider-dev /bin/echo "test alive" > /dev/null 2>&1;
    then
        docker exec -i -t amwatcher-spider-dev \
            python /usr/src/app/start.py --env test -c -a -s --analyze_all
    else
        echo 'You must start container amwatcher-spider-dev first!'
    fi
}

function clear_unused() {
    echo 'Clearing unused docker images and volumes...'
    docker images -qf dangling=true | xargs docker rmi --force
    docker volume ls -qf dangling=true |xargs docker volume rm --force
}

# MAIN
if [ $# -eq 0 ];
then
    help
fi

case $1 in
    loop)
        loop
        ;;
    tunnel)
        tunnel
        loop
        ;;
    start)
        build_container
        ;;
    run)
        run_test
        ;;
    shell)
        docker exec -i -t $CONTAINER /bin/bash
        ;;
    stop)
        docker kill $CONTAINER
        ;;
    rmc)
        docker kill $CONTAINER
        docker rm $CONTAINER
        ;;
    rmi)
        docker kill $CONTAINER
        docker rm $CONTAINER
        docker rmi $IMAGE
        ;;
    trim)
        clear_unused
        ;;
    *)
        help
        ;;
esac

