import asyncio
import logging
import json
import time
import os
from glob import glob
from pprint import pformat

from collections import namedtuple
from queue import Queue

from aioquic.quic.configuration import QuicConfiguration

from adaptive.abr import BasicABR
from adaptive.mpc import MPC
from adaptive.bola import Bola
from adaptive.BBA0 import BBA0
from adaptive.BBA2 import BBA2

from clients.build import run

import config
import logger

logger = logger.logger("DASH client")

adaptiveInfo = namedtuple("AdaptiveInfo",
                          'segment_time bitrates segments')
downloadInfo = namedtuple("DownloadInfo",
                          'index file_name url quality resolution size downloaded time')


def segment_download_info(manifest, fname, size, idx, url, quality, resolution, time):
    if size <= 0:
        return downloadInfo(index=idx, file_name=None, url=None, quality=quality, resolution=resolution, size=0, downloaded=0, time=0)
    else:
        return downloadInfo(index=idx, file_name=fname, url=url, quality=quality, resolution=resolution, size=size, downloaded=size, time=time)


async def perform_download(configuration: QuicConfiguration, args, urlsToDwnld = None) -> None:
	if args.urls is None:
		args.urls = config.URLS
	if urlsToDwnld:
		logger.debug('downloading segment urls :{}'.format(urlsToDwnld))
		res = await run(
				configuration=configuration,
				# urls=args.urls,
				urls= urlsToDwnld,
				data=args.data,
				include=args.include,
				legacy_quic=args.legacy_quic,
				output_dir=args.output_dir,
				local_port=args.local_port,
				zero_rtt=args.zero_rtt,
				session_ticket=args.session_ticket,
			)
	else:
		logger.debug('downloading manifest urls:{}'.format(args.urls))
		res = await run(
				configuration=configuration,
				urls=args.urls,
				data=args.data,
				include=args.include,
				legacy_quic=args.legacy_quic,
				output_dir=args.output_dir,
				local_port=args.local_port,
				zero_rtt=args.zero_rtt,
				session_ticket=args.session_ticket,
			)
	return res

def select_abr_algorithm(manifest_data, args):
	if args.abr == "BBA0":
		return BBA0(manifest_data)
	elif args.abr == 'Bola':
		return Bola(manifest_data)
	elif args.abr == 'tputRule':
		return BasicABR(manifest_data)
	elif args.abr == 'MPC':
		return MPC(manifest_data)
	elif args.abr == 'BBA2':
		return BBA2(manifest_data)
	else:
		logger.error("Error!! No right rule specified")
		return


class DashClient:
	def __init__(self, configuration: QuicConfiguration, args):

		logger.info(configuration)
		logger.info(args)
		self.configuration = configuration
		self.args = args
		self.manifest_data = None
		self.latest_tput = 0

		self.lock = asyncio.Lock()
		self.totalBuffer = args.buffer_size
		self.currBuffer = 0
		self.abr_algorithm = None
		self.segment_baseName = None

		self.lastDownloadSize = 0
		self.lastDownloadTime = 0
		self.segmentQueue = asyncio.Queue()
		self.frameQueue = asyncio.Queue()

		self.perf_parameters = {}
		self.perf_parameters['startup_delay'] = 0
		self.perf_parameters['total_time_elapsed'] = 0
		self.perf_parameters['bitrate_change'] = []
		self.perf_parameters['prev_rate'] = 0
		self.perf_parameters['change_count'] = 0
		self.perf_parameters['rebuffer_time'] = 0.0
		self.perf_parameters['avg_bitrate'] = 0.0
		self.perf_parameters['avg_bitrate_change'] = 0.0
		self.perf_parameters['rebuffer_count'] = 0
		self.perf_parameters['tput_observed'] = []

	async def download_manifest(self) -> None:
		#TODO: Cleanup: globally intakes a list of urls, while here
		# we only consider a single urls per event.
		logger.info("Downloading Manifest file")
		logger.info(self.args)

		res = await perform_download(self.configuration, self.args)
		self.baseUrl, self.filename = os.path.split(self.args.urls[0])

		# logger.info(res[0][3])

		self.manifest_data = json.loads(res[0][3])
		logger.info(self.manifest_data)
		self.lastDownloadSize = res[0][0]
		self.latest_tput = res[0][1]
		self.lastDownloadTime = res[0][2]

	async def dash_client_set_config(self) -> None:
		logger.info("DASH client initialization in process")
		await self.download_manifest()
		self.abr_algorithm = select_abr_algorithm(self.manifest_data, self.args)
		self.currentSegment = self.manifest_data['start_number'] -1
		self.totalSegments = self.getTotalSegments()

	def getTotalSegments(self):
		return self.manifest_data['total_segments']

	def getDuration(self):
		return self.manifest_data['total_duration']

	def getCorrespondingBitrateIndex(self, bitrate):
		for i, b in enumerate(self.manifest_data['bitrates_kbps']):
			if b == bitrate:
				return i + 1
		return -1

	def latest_segment_Throughput_kbps(self):
		# returns throughput value of last segment downloaded in kbps
		return self.latest_tput
	
	# async def fetchNextSegment(self, segment_list, bitrate = 0):
	async def fetchNextSegment(self, segmentNum, bitrate = 0):
		# if not bitrate:
		# 	return

		segment_Duration = 0
		bitIdx = bitrate
		# for i, b in enumerate(self.manifest_data['bitrates_kbps']):
		# 	if b == bitrate:
		# 		segment_Duration = int(self.manifest_data['segment_duration_ms']) / int(self.manifest_data['timescale'])
		# 		bitIdx = i+1
		# 		break

		# for fname in sorted(glob(segment_list)):
		# 	_, self.segment_baseName = fname.rsplit('/', 1)
		# 	# self.args.urls[0] = self.baseUrl + '/' + str(os.stat(fname).st_size)
		# 	logger.info('aakash '+self.args.urls[0])
		# 	start = time.time()
		# 	res = await perform_download(self.configuration, self.args)
		# 	elapsed = time.time() - start


		
		# _, self.segment_baseName = fname.rsplit('/', 1)
		# self.args.urls[0] = self.baseUrl + '/' + str(os.stat(fname).st_size)

		urlsToDwnld:List[str] = []

		for i in range(3):
			t_str = self.baseUrl + '/video_' + str(bitIdx) + '_dash' + str(segmentNum+i)
			urlsToDwnld.append(t_str)

		# self.args.urls[0] = self.baseUrl + '/video_' + str(bitIdx) + '_dash' + str(segmentNum) 
		logger.info('aakash :{}'.format(urlsToDwnld))
		start = time.time()
		# res = await perform_download(self.configuration, self.args)
		res = await perform_download(self.configuration, self.args, urlsToDwnld)

		elapsed = time.time() - start

		data = res[0][0]
		if data is not None:
			self.lastDownloadTime = elapsed
			self.lastDownloadSize = data
			self.latest_tput =  res[0][1]

			await self.segmentQueue.put(urlsToDwnld)

			# QOE parameters update
			self.perf_parameters['bitrate_change'].append((self.currentSegment + 1,  bitrate))
			self.perf_parameters['tput_observed'].append((self.currentSegment + 1,  res[0][1]))
			self.perf_parameters['avg_bitrate'] += bitrate
			self.perf_parameters['avg_bitrate_change'] += abs(bitrate - self.perf_parameters['prev_rate'])

			if not self.perf_parameters['prev_rate'] or self.perf_parameters['prev_rate'] != bitrate:
				self.perf_parameters['prev_rate'] = bitrate
				self.perf_parameters['change_count'] += 1

			self.currentSegment += 1
			async with self.lock:
					self.currBuffer += segment_Duration

			ret = True
		else:
			logger.fatal("Error: downloaded segment is none!! Playback will stop shortly")
			ret = False
		return ret

	async def download_segment(self) -> None:
		# if config.NUM_SERVER_PUSHED_FRAMES is not None:
		# 	self.currentSegment = config.NUM_SERVER_PUSHED_FRAMES + 1
		# else:
		# 	self.currentSegment += 1

		while self.currentSegment < self.totalSegments:
			async with self.lock:
				currBuff = self.currBuffer

			segment_Duration = int(self.manifest_data['duration']) / int(self.manifest_data['timescale'])

			playback_stats = {}
			playback_stats["lastTput_kbps"] = self.latest_segment_Throughput_kbps()
			playback_stats["currBuffer"] = currBuff
			playback_stats["segment_Idx"] = self.currentSegment + 1

			logger.info(pformat(playback_stats))

			if self.totalBuffer - currBuff >= segment_Duration:
				rateNext = self.abr_algorithm.NextSegmentQualityIndex(playback_stats)
				segment_resolution = self.manifest_data['bitrates'][rateNext]
				# fName = "htdocs/dash/" + segment_resolution + "/out/frame-" + str(self.currentSegment) + "-" + segment_resolution + "-*"
				
				# if await self.fetchNextSegment(fName, rateNext):
				logger.info('aakash {}, {}'.format(self.currentSegment+1, rateNext))
				if await self.fetchNextSegment(self.currentSegment+1, rateNext):
					dp = segment_download_info(self.manifest_data, self.segment_baseName, self.lastDownloadSize, self.currentSegment, self.args.urls, rateNext, segment_resolution, self.lastDownloadTime)
					logger.info(dp)
				else:
					logger.info("breaking")
					break
			else:
				asyncio.sleep(1)

		await self.segmentQueue.put("Download complete")
		logger.info("All the segments have been downloaded")

	#emulate playback of frame scenario
	async def playback_frames(self) -> None:
		#Flag to mark whether placback has started or not.
		has_playback_started = False
		while True:
			await asyncio.sleep(1)
			rebuffer_start = time.time()
			frame = await self.frameQueue.get()
			rebuffer_elapsed = time.time() - rebuffer_start

			if frame == "Decoding complete":
				logger.info("All the segments have been played back")
				break

			if not has_playback_started:
				has_playback_started = True
				self.perf_parameters['startup_delay'] = time.time()
			else:
				self.perf_parameters['rebuffer_time'] += rebuffer_elapsed

			if rebuffer_elapsed > 0.0001:
				logger.info('rebuffer_time:{}'.format(rebuffer_elapsed))
				self.perf_parameters['rebuffer_count'] += 1
			async with self.lock:
				self.currBuffer -= 2
			logger.info("Played segments: {}".format(frame))

	#emulate decoding the frame scenario
	async def decode_frames(self) -> None:
		while True:
			await asyncio.sleep(1)
			segment = await self.segmentQueue.get()
			if segment == "Download complete":
				logger.info("All the segments have been decoded")
				await self.frameQueue.put("Decoding complete")
				break

			logger.info("Decoded segments: {}".format(segment))
			await self.frameQueue.put(segment)

	async def player(self) -> None:
		await self.dash_client_set_config()

		tasks = [asyncio.ensure_future(self.download_segment()),
				asyncio.ensure_future(self.decode_frames()),
				asyncio.ensure_future(self.playback_frames())]

		await asyncio.gather(*tasks)

		# self.perf_parameters['avg_bitrate'] /= self.totalSegments
		# self.perf_parameters['avg_bitrate_change'] /= (self.totalSegments - 1)
