#!/bin/bash

echo "--- Activating virtual environment ---"

# if you prefer to use conda, add the following line changing conda for the model you are using
# source ~/conda/etc/profile.d/conda.sh

# also add this line with the actual name of your environment
# conda activate environment
# if you do the previous you should either remove or comment the following if statement
if [ -d ".venv/" ]; then
    source ./.venv/bin/activate
else
    echo "No virtual environment found, please create one and install the requirements."
    echo "If you are using Conda, please add the necessary lines in main.sh"
    exit 1
fi

confirm()
{
    local prompt="$1"
    local default="$2"
    local options

    [[ "$default" == "Y" ]] && options="[Y/n]" || options="[y/N]"

    echo ""
    read -p "$prompt $options: " response
    response="${response:-$default}"

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
        ;;
        *)
            return 1
        ;;
    esac
}

#Checks if the file exists and is not empty.
#Returns True if file exists and has content, False otherwise.
file_exists()
{
    local path="$1"

    if [ -s "$path" ]; then
        return 0
    else
        echo "You can not execute this action because "${path##*/}" does not exists at "$path", or it's empty."
        return 1
    fi

}

# stops the program to ensure it does not carry on after an error
shutdown()
{
    echo "Shutting down..."
    deactivate # if usin conda, change this to conda deactivate
    exit 1
}

# Exports variables from config.json
eval $(python -c "
import json
c = json.load(open('config.json'))
print(f'FINAL_PATH=\"{c[\"path_final_csv\"]}\"')
print(f'PATH_USER_CSV=\"{c[\"path_user_csv\"]}\"')
print(f'MODIFIED_AIRING=\"{c[\"path_modified_airing\"]}\"')
print(f'HISTORICAL_CSV=\"{c[\"path_historical_csv\"]}\"')
")
FINAL_CSV="${FINAL_PATH##*/}"
USER_CSV="${PATH_USER_CSV##*/}"

# the program needs these files to exist and to have information
for path in "$MODIFIED_AIRING" "$HISTORICAL_CSV"; do
    if [ ! -s "$path" ]; then
        echo ""
        echo "ERROR: File "${path##*/}" does not exists at "$path", or it's empty."
        shutdown
    fi
done

OPTIONS=( "Sync your csv" "Add work" "Remove Work" "Dashboard" "Update Airing" "Update Final" "Fetch From Anilist" "Exit" )
len=${#OPTIONS[@]}

args=("$@")
len_args="$#"
# no argument, a single option number (one digit, so at most 9 options) or "6 --all" to update every work of final.csv
[[ $# -eq 0 || ( $# -eq 1 && $1 =~ ^[1-$len]$ ) || ( $# -eq 2 && $1 == 6 && $2 == --all ) ]] \
    || { echo ""; echo "Usage: ./main.sh [1-$len] | ./main.sh 6 --all"; shutdown; }

while true; do
    if [ "$len_args" -ne 0 ]; then
        action="${args[0]}"
        flag="${args[1]}"
        from_args=true
        len_args=0
    else
        flag=""
        from_args=false
        echo ""
        echo "What do you want to do?"

        for ((i=0; i<$len; i++)); do
            echo ""$((i+1))": "${OPTIONS[$i]}""
        done

        # no more input (piped or closed stdin, ctrl + d): exit instead of looping forever
        read -p "Please enter the number: " action || break
    fi

    case "$action" in
        1)
            if file_exists "$PATH_USER_CSV"; then
                echo ""
                echo -n "This action will match "$USER_CSV" with anime.csv and it will create "$FINAL_CSV" with all"
                echo " the matches and the complete information"
                if confirm "Do you want to proceed? " "Y"; then
                    echo "Creating "$FINAL_CSV" please wait a moment..."
                    python -m src.pipeline.match_name || shutdown
                else
                    echo "Going back to actions."
                fi
            fi
        ;;
        2)
            echo ""
            python -m src.manual.add_work || shutdown
        ;;
        3)
            echo ""
            if file_exists "$FINAL_PATH"; then
                python -m src.manual.remove_work || shutdown
            fi
        ;;
        4)
            echo ""
            file_exists "$FINAL_PATH" && {
                echo "To stop the app press \"ctrl + c\""
                python -m streamlit run ./streamlit_app.py
            }
        ;;
        5)
            echo ""
            echo -n "This action will fetch from Anilist every releasing work and the ones yet to release from the current and "
            echo "next season into airing_anime.csv, then it will clean that file and concatenate it with anime.csv"

            if confirm "Do you want to proceed?" "Y"; then
                echo "--------------------------------"
                python -m src.pipeline.fetch_airing && python -m src.pipeline.cleanup_airing \
                    && python -m src.pipeline.concatenate || shutdown
            else
                echo "Going back to actions."
            fi
        ;;
        6)
            echo ""
            if file_exists "$FINAL_PATH"; then
                # from the args there is no menu: "6" updates the airing works and "6 --all" every work
                if [ "$flag" == "--all" ]; then
                    choice=2
                elif [ "$from_args" == true ]; then
                    choice=1
                else
                    echo "How do you want to update "$FINAL_CSV"?"
                    echo "1: Airing works, with the information from airing_anime_M.csv. The ones still releasing or yet to"
                    echo "   release in "$FINAL_CSV" that are no longer airing get the information from anime.csv"
                    echo "2: Every work, with the information from anime.csv"
                    echo "3: Go back to actions"
                    read -p "Please enter the number: " choice
                fi

                case "$choice" in
                    1) python -m src.pipeline.update_final_csv || shutdown ;;
                    2) python -m src.pipeline.update_final_csv --all || shutdown ;;
                    *) echo "Going back to actions." ;;
                esac
            fi
        ;;
        7)
            echo ""
            python -m api.get_anime || shutdown
        ;;
        8)
            break
        ;;
        *)
            echo ""
            echo "You need to choose a number between 1 and "$len", please try again."
        ;;
    esac
done

echo ""
echo "-- Closing virtual environment ---"

# conda deactivate
deactivate # remove or commment this line if you are using conda and add the previous one

exit 0
