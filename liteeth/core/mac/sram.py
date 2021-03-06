from liteeth.common import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect.csr_eventmanager import *



class LiteEthMACSRAMWriter(Module, AutoCSR):
    def __init__(self, dw, depth, nslots=2):
        self.sink = sink = stream.Endpoint(eth_phy_description(dw))
        self.crc_error = Signal()

        slotbits = max(log2_int(nslots), 1)
        lengthbits = log2_int(depth*4)  # length in bytes

        self._slot = CSRStatus(slotbits)
        self._length = CSRStatus(lengthbits)

        self.submodules.ev = EventManager()
        self.ev.available = EventSourceLevel()
        self.ev.finalize()

        # # #

        # packet dropped if no slot available
        sink.ready.reset = 1

        # length computation
        increment = Signal(3)
        self.comb += \
            If(sink.last_be[3],
                increment.eq(1)
            ).Elif(sink.last_be[2],
                increment.eq(2)
            ).Elif(sink.last_be[1],
                increment.eq(3)
            ).Else(
                increment.eq(4)
            )
        counter = Signal(lengthbits)
        counter_reset = Signal()
        counter_ce = Signal()
        self.sync += \
            If(counter_reset,
                counter.eq(0)
            ).Elif(counter_ce,
                counter.eq(counter + increment)
            )

        # slot computation
        slot = Signal(slotbits)
        slot_ce = Signal()
        self.sync += If(slot_ce, slot.eq(slot + 1))

        ongoing = Signal()

        # status fifo
        fifo = stream.SyncFIFO([("slot", slotbits), ("length", lengthbits)], nslots)
        self.submodules += fifo

        # fsm
        fsm = FSM(reset_state="IDLE")
        self.submodules += fsm

        fsm.act("IDLE",
            If(sink.valid,
                If(fifo.sink.ready,
                    ongoing.eq(1),
                    counter_ce.eq(1),
                    NextState("WRITE")
                )
            )
        )
        fsm.act("WRITE",
            counter_ce.eq(sink.valid),
            ongoing.eq(1),
            If(sink.valid & sink.last,
                If((sink.error & sink.last_be) != 0,
                    NextState("DISCARD")
                ).Else(
                    NextState("TERMINATE")
                )
            )
        )
        fsm.act("DISCARD",
            counter_reset.eq(1),
            NextState("IDLE")
        )
        self.comb += [
            fifo.sink.slot.eq(slot),
            fifo.sink.length.eq(counter)
        ]
        fsm.act("TERMINATE",
            counter_reset.eq(1),
            slot_ce.eq(1),
            fifo.sink.valid.eq(1),
            NextState("IDLE")
        )
        self.comb += [
            fifo.source.ready.eq(self.ev.available.clear),
            self.ev.available.trigger.eq(fifo.source.valid),
            self._slot.status.eq(fifo.source.slot),
            self._length.status.eq(fifo.source.length),
        ]

        # memory
        mems = [None]*nslots
        ports = [None]*nslots
        for n in range(nslots):
            mems[n] = Memory(dw, depth)
            ports[n] = mems[n].get_port(write_capable=True)
            self.specials += ports[n]
        self.mems = mems

        cases = {}
        for n, port in enumerate(ports):
            cases[n] = [
                ports[n].adr.eq(counter[2:]),
                ports[n].dat_w.eq(sink.data),
                If(sink.valid & ongoing,
                    ports[n].we.eq(0xf)
                )
            ]
        self.comb += Case(slot, cases)


class LiteEthMACSRAMReader(Module, AutoCSR):
    def __init__(self, dw, depth, nslots=2):
        self.source = source = stream.Endpoint(eth_phy_description(dw))

        slotbits = max(log2_int(nslots), 1)
        lengthbits = log2_int(depth*4)  # length in bytes
        self.lengthbits = lengthbits

        self._start = CSR()
        self._ready = CSRStatus()
        self._slot = CSRStorage(slotbits)
        self._length = CSRStorage(lengthbits)

        self.submodules.ev = EventManager()
        self.ev.done = EventSourcePulse()
        self.ev.finalize()

        # # #

        # command fifo
        fifo = stream.SyncFIFO([("slot", slotbits), ("length", lengthbits)], nslots)
        self.submodules += fifo
        self.comb += [
            fifo.sink.valid.eq(self._start.re),
            fifo.sink.slot.eq(self._slot.storage),
            fifo.sink.length.eq(self._length.storage),
            self._ready.status.eq(fifo.sink.ready)
        ]

        # length computation
        counter = Signal(lengthbits)
        counter_reset = Signal()
        counter_ce = Signal()
        self.sync += \
            If(counter_reset,
                counter.eq(0)
            ).Elif(counter_ce,
                counter.eq(counter + 4)
            )


        # fsm
        last  = Signal()

        fsm = FSM(reset_state="IDLE")
        self.submodules += fsm

        fsm.act("IDLE",
            If(fifo.source.valid,
                counter_ce.eq(1),
                NextState("SEND")
            )
        )
        length_lsb = fifo.source.length[0:2]
        self.comb += [
            If(last,
                If(length_lsb == 3,
                    source.last_be.eq(0b0010)
                ).Elif(length_lsb == 2,
                    source.last_be.eq(0b0100)
                ).Elif(length_lsb == 1,
                    source.last_be.eq(0b1000)
                ).Else(
                    source.last_be.eq(0b0001)
                )
            )
        ]
        fsm.act("SEND",
            source.valid.eq(1),
            source.last.eq(last),
            If(source.ready,
                counter_ce.eq(1),
                If(last,
                    NextState("TERMINATE")
                )
            )
        )
        fsm.act("TERMINATE",
            fifo.source.ready.eq(1),
            self.ev.done.trigger.eq(1),
            counter_reset.eq(1),
            NextState("IDLE")
        )

        # last computation
        self.comb += last.eq(counter >= fifo.source.length)

        # memory
        rd_slot = fifo.source.slot

        mems = [None]*nslots
        ports = [None]*nslots
        for n in range(nslots):
            mems[n] = Memory(dw, depth)
            ports[n] = mems[n].get_port()
            self.specials += ports[n]
        self.mems = mems

        cases = {}
        for n, port in enumerate(ports):
            self.comb += ports[n].adr.eq(counter[2:])
            cases[n] = [source.data.eq(port.dat_r)]
        self.comb += Case(rd_slot, cases)


class LiteEthMACSRAM(Module, AutoCSR):
    def __init__(self, dw, depth, nrxslots, ntxslots):
        self.submodules.writer = LiteEthMACSRAMWriter(dw, depth, nrxslots)
        self.submodules.reader = LiteEthMACSRAMReader(dw, depth, ntxslots)
        self.submodules.ev = SharedIRQ(self.writer.ev, self.reader.ev)
        self.sink, self.source = self.writer.sink, self.reader.source
