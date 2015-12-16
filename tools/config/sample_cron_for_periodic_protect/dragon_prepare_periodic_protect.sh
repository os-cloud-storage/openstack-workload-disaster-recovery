# prepare for set time peridoc run of dragon protect

function usage
{
   echo " Usage : ./dragon_prepare_periodic_protect.sh -i <workload_id> [-c | --consistent] [-t <cron time string>]"
   echo "       note: for -t  see Linux crontab example. default assumed : midnight daily i.e '0,0,*,*,*']] "
   echo "       use commas instead of spaces as separators between fields in the cron time string !"
}

function prepare_protect_script
{
 echo ". $user_home/openrc" >& $user_home/dragon_periodic_protect.sh
 echo "/usr/bin/dragon protect $optional_param   $workload_id >&  protect.dat" >> $user_home/dragon_periodic_protect.sh
 chmod +x $user_home'/dragon_periodic_protect.sh'
}

function handle_cron
{
 if [ $cron_time = "default" ]; then
        echo  '0 0 * * *  '$user' '$user_home'/dragon_periodic_protect.sh' >& /etc/cron.d/dragon_protect_periodic
 else
        replacor="\x2a"
        cron_time=${cron_time//'*'/$replacor}  # replace each '*' with its ascii code '\x2a'
        replacor="\x20"
        cron_time=${cron_time//','/$replacor}  # replace each ',' with space  code '\x20'

        echo -e $cron_time" "$user" "$user_home"/dragon_periodic_protect.sh" >& /etc/cron.d/dragon_protect_periodic

 fi
}

#main program 

cron_time="default"
optional_param=" "
workload_id=""
while [ "$1" != "" ]; do
    case $1 in
	-i | --workload_id )   	shift
                                if [ -z $1 ] || [ $1 = '-t' ] || [ $1 = '-c' ]; then
                                        usage
					exit
                                fi
				workload_id=$1
				;;
        -c | --consistent )     optional_param='--consistent true'      
                                ;;
	-t | --timeframe )      shift
				if [ -z $1 ] || [ $1 = '-i'i ] || [ $1 = '-c' ]; then
					usage
					exit
				fi
				cron_time=$1
				;;					
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

user=`whoami`
#echo "user= "$user
if [ $user != 'root' ]; then
	user_home='/home/'$user
else
	user_home='/root'
fi
#echo $user_home
if   [ -z $1 ]; then
	usage
elif  [ $workload_id != "" ]; then
	prepare_protect_script
	handle_cron
else
	usage
fi

exit

