#!/usr/bin/env python3
import sys
import os
import signal
from traceback import print_exc
from subprocess import Popen, PIPE
from threading import Thread
from queue import SimpleQueue
from typing import Optional, TypeVar, List
from functools import wraps


queue = SimpleQueue() # type: SimpleQueue[list[bytes]]

T = TypeVar("T")

def none_throws(optional: Optional[T], message: str = "Unexpected `None`") -> T:
	if optional is None:
		raise AssertionError(message)
	return optional


class RaisingThread(Thread):
	"""Thread that will raise any uncaught exceptions in the thread in the
	parent once it joins again."""

	exception: Optional[Exception]

	def run(self):
		self.exception = None
		try:
			super().run()
		except Exception as exc:
			self.exception = exc

	def join(self, timeout:float=None):
		super().join(timeout=timeout)
		if self.exception is not None:
			raise self.exception


def split(column, queue, fin, fout):
	try:
		for line in fin:
			fields = line.rstrip(b'\r\n').split(b'\t')
			field = fields[column] # Doing column selection first so that if this fails, we haven't already written it to the queue
			queue.put(fields[:column] + fields[(column+1):])
			fout.write(field + b'\n')
		fout.close()
	except BrokenPipeError:
		pass
	finally:
		queue.put(None) # End indicator
		fin.close()

def merge(column, queue, fin, fout):
	try:
		for field in fin:
			fields = queue.get()
			if fields is None:
				raise RuntimeError('Subprocess produced more lines of output than it was given.')
			fout.write(b'\t'.join(fields[:column] + [field.rstrip(b'\n')] + fields[column:]) + b'\n')
		if queue.get() is not None:
			raise RuntimeError('Subprocess produced fewer lines than it was given.')
		fout.close()
	except BrokenPipeError:
		pass
	finally:
		fin.close()


def main():
	column = int(sys.argv[1])

	child = Popen(sys.argv[2:], stdin=PIPE, stdout=PIPE)

	feeder = RaisingThread(target=split, args=[column, queue, sys.stdin.buffer, none_throws(child).stdin])
	feeder.start()

	consumer = RaisingThread(target=merge, args=[column, queue, none_throws(child).stdout, sys.stdout.buffer])
	consumer.start()

	retval = child.wait()

	try:
		feeder.join()
		consumer.join()
	except Exception as e:
		print(f'Error: {e}', file=sys.stderr)
		# Only change retval if it wasn't already non-zero by the program.
		if retval == 0:
			retval = 1

	sys.exit(retval)

if __name__ == '__main__':
	main()
