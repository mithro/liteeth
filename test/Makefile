PYTHON = python3

CMD = $(PYTHON)

model_tb:
	PYTHONPATH=./ $(CMD) ./model/mac.py
	PYTHONPATH=./ $(CMD) ./model/arp.py
	PYTHONPATH=./ $(CMD) ./model/ip.py
	PYTHONPATH=./ $(CMD) ./model/udp.py
	PYTHONPATH=./ $(CMD) ./model/icmp.py
	PYTHONPATH=./ $(CMD) ./model/etherbone.py

mac_core_tb:
	$(CMD) mac_core_tb.py

mac_wishbone_tb:
	$(CMD) mac_wishbone_tb.py

arp_tb:
	$(CMD) arp_tb.py

ip_tb:
	$(CMD) ip_tb.py

udp_tb:
	$(CMD) udp_tb.py

icmp_tb:
	$(CMD) icmp_tb.py

etherbone_tb:
	$(CMD) etherbone_tb.py

example_designs:
	cd ../example_designs && $(PYTHON) make.py -t base -s BaseSoC -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t base -s BaseSoCDevel -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t udp -s UDPSoC -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t udp -s UDPSoCDevel -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t etherbone -s EtherboneSoC -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t etherbone -s EtherboneSoCDevel -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t tty -s TTYSoC -p kc705 -Ob run False build-bitstream
	cd ../example_designs && $(PYTHON) make.py -t tty -s TTYSoCDevel -p kc705 -Ob run False build-bitstream

all: model_tb mac_core_tb arp_tb ip_tb udp_tb icmp_tb etherbone_tb example_designs