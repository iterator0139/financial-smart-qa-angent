for env in $(conda env list | grep -v '#' | awk '{print $1}'); do
  conda env export -n $env > /tmp/${env}.yml
done
