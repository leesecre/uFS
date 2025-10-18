# How to attach GDB to microbench

Find out benchmark command from the printed log.

If you're running uFS, just run it as below:

```shell
gdb --args <command>
```

If you're running different systems like Oxbow or Ext4, coordinator is required.
Find out coordinator command from the printed log.

Run the coordinator first as root.

```shell
sudo /path/to/coordinator
```

Run the benchmark with gdb as mentioned above.
