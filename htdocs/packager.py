# this file creates folders for each video and 
# put required Iframes Codes, Pframe Codes, and flows in 
# respective folders

import os
import _pickle as pickle
import numpy as np
from PIL import Image 
import glob

import logger
import argparse
logger = logger.logger("Packager")

################################ video packager config start ################################
iCodePath = './icodes'
# as present in above path
iCodeFileNameFormat = 'video_$videoName$_cif_$frameNum$.png.codes.npz'

pCodePath = './pcodes/output_$trackNum$/codes'
# as present in above path
pCodeFileNameFormat = 'video_$videoName$_cif_$frameNum$.png.codes.npz'

pFlowsPath = './pflows'
# as present in above path
pFlowsFileNameFormat = ['video_$videoName$_cif_$frameNum$_after_flow_x_0001.jpg', 
						'video_$videoName$_cif_$frameNum$_after_flow_y_0001.jpg',
						'video_$videoName$_cif_$frameNum$_before_flow_x_0001.jpg',
						'video_$videoName$_cif_$frameNum$_before_flow_y_0001.jpg']

# videoNames = ['all']
videoNames = ['all']

saveToPath = './static' 

videoSegmentPcodeNameFormat = 'video_t_$trackNum$_s_$segmentNum$.p'
videoSegmentIcodeNameFormat = 'video_s_$segmentNum$.p'

replicateFactor = 5

totalFrames = 97

framesPerSegment = 97

iCodeFrequency = 12

iCodePerSegment = 1 + (framesPerSegment - 1) // iCodeFrequency
totalSegments = totalFrames // framesPerSegment

totalTracks = 10
################################ video packager config end ##################################

################################# Assumptions ################################## 
# Frames start from number 1.
# 
# After pickling file extension should be .p and before .p 4 characters will be segment number.
# otherwise replicate function will break.
# 
################################# Assumptions ################################## 
def isIcodeFrame(frameNum):
			# print(frameNum)
	if (frameNum - 1) % iCodeFrequency == 0:
		return True
	return False

class packager:

	def __init__(self,args):
		self.args = args
		logger.info('')
		logger.info('packaging video:{}'.format(self.args.vidName))


	def replicateFrames(self, factor = 2):
		if factor <= 1:
			return

		segmentFrameNames = glob.glob('./all/frames/*.p')
		logger.error(f'total files in folder{len(segmentFrameNames)}')
		if len(segmentFrameNames) > 4445:
			return

		# os.system('cp ' + sfn + ' ' + sfn[:-6] + str(currSegNum).zfill(4)+'.p')
		# iFrameFile = "video_segment_$segNum$_frame_$frameNum$.p"
		# pFrameFile = "video_track_$trackNum$_segment_$segNum$_frame_$frameNum$.p"
# 14-19
		for sfn in segmentFrameNames:
			# logger.error(sfn)
			for segNum in range(2, factor+1):
				newFileName = sfn[:-17] + str(segNum).zfill(4) + sfn[-13:]
				os.system('cp ' + sfn + ' ' + newFileName)
		return



		

		
	def replicateSegment(self, factor = 2):
		if factor <= 1:
			return
		
		segmentFname = glob.glob(os.path.join(saveToPath, self.args.vidName, 'icodes/*.p'))
		segmentPresentInFolder = len(segmentFname)
		logger.info('Total number of segment already in {} video folder:{}'.format(self.args.vidName, segmentPresentInFolder))
		
		if segmentPresentInFolder >= 100:
			logger.info('Way too many segments already present. Use them only. Returning')
			return
		for sfn in segmentFname:
			currSegNum = int(sfn[-6:-2]) + segmentPresentInFolder
			for i in range(1, factor):
				os.system('cp ' + sfn + ' ' + sfn[:-6] + str(currSegNum).zfill(4)+'.p')
				currSegNum += segmentPresentInFolder

		segmentFname = glob.glob(os.path.join(saveToPath, self.args.vidName, 'pcodes/*.p'))
		
		for sfn in segmentFname:
			currSegNum = int(sfn[-6:-2]) + segmentPresentInFolder
			for i in range(1, factor):
				os.system('cp ' + sfn + ' ' + sfn[:-6] + str(currSegNum).zfill(4)+'.p')
				currSegNum += segmentPresentInFolder


	def packPcodesFlowsForTrack(self, trackNum):



		currSegmentNum = 1
		currFrame = 1

		for i in range(1, totalSegments+1):
			pCodesObj = []

			for j in range(1, framesPerSegment+1):

				pCodeFlowFrm = []
				if isIcodeFrame(currFrame):
					currFrame += 1
					continue
				
				# pCodeFileNameFormat = 'video_$videoName$_cif_$frameNum$.png.codes.npz'
				pcFile = pCodeFileNameFormat \
						.replace('$videoName$',self.args.vidName) \
						.replace('$frameNum$', str(currFrame).zfill(4))
				
				# logger.info('Pcode file name:{}'.format(pcFile))

				pcTrackPath = pCodePath.replace('$trackNum$', str(trackNum))

				with open(os.path.join(pcTrackPath, pcFile), 'rb') as f:
					pCodeFlowFrm.append(f.read())

				# pFlowsFileNameFormat = ['video_$videoName$_cif_$frameNum$_after_flow_x_0001.jpg', 
				for flowFileNameFormat in pFlowsFileNameFormat:
					flFile = flowFileNameFormat \
								.replace('$videoName$', self.args.vidName) \
								.replace('$frameNum$', str(j).zfill(4))
					
					# logger.info('Flow file Name:{}'.format(flFile))
					with open(os.path.join(pFlowsPath, flFile), 'rb') as f:
						pCodeFlowFrm.append(f.read())
				
				pCodesObj.append(pCodeFlowFrm)
				currFrame += 1
			
			pCodePckFile = os.path.join(saveToPath,self.args.vidName, 'pcodes', videoSegmentPcodeNameFormat)
			pCodePckFile = pCodePckFile \
							.replace('$segmentNum$', str(currSegmentNum).zfill(4)) \
							.replace('$trackNum$',str(trackNum).zfill(4))

			logger.info('pCodePckFile Name:{}'.format(pCodePckFile))
				
			with open(pCodePckFile, 'wb') as f:
				pickle.dump(pCodesObj, f)


	def packPcodesFlows(self):		

		for t in range(1, totalTracks+1):
			self.packPcodesFlowsForTrack(t)

	def packIcodes(self):

		currIframe = 1
		for currSegmentNum in range(1, totalSegments+1):

			iCodesObj = []

			for j in range(iCodePerSegment):
				# iCodeFileNameFormat = 'video_$videoName$_cif_$frameNum$.png.codes.npz'
				icFile = iCodeFileNameFormat \
					.replace('$videoName$',self.args.vidName) \
					.replace('$frameNum$',str(currIframe).zfill(4))

				# logger.info('Icode file name:{}'.format(icFile))

				with open(iCodePath+ '/' +icFile, 'rb') as f:
					iCodesObj.append(f.read())
				
				currIframe += iCodeFrequency

			iCodePckFile = os.path.join(saveToPath, self.args.vidName , 'icodes',videoSegmentIcodeNameFormat)
			iCodePckFile = iCodePckFile.replace('$segmentNum$', str(currSegmentNum).zfill(4))
			logger.info('iCodePckFile Name:{}'.format(iCodePckFile))

			with open(iCodePckFile, 'wb') as f:
				pickle.dump(iCodesObj, f)

			# videoSegmentIcodeNameFormat = 'video_$segmentNum$.pickle$'

	def createFolders(self):
		videoName = self.args.vidName
		p = saveToPath + '/' + videoName + '/pcodes'
		i = saveToPath + '/' + videoName + '/icodes'
		allInOne = saveToPath + '/' + videoName + '/frames'
		if not os.path.isdir(p):
			os.makedirs(p)
		if not os.path.isdir(i):
			os.makedirs(i)
		if not os.path.isdir(allInOne):
			os.makedirs(allInOne)
		logger.debug('folder created')


	def createPickledFrames(self):

		def isIcodeFrame(frameNum):
			# print(frameNum)
			if (frameNum - 1) % iCodeFrequency == 0:
				return True
			return False


		currFrame = 1
		for currSegment in range(1, totalSegments + 1):
			for currFrame in range(1,totalFrames + 1):

				fileNameToSave = ''
				iCodesObj = []
				if isIcodeFrame(currFrame):
					# to pack icode in a .p file. it will be list of single element. icode of that frame.
					icFile = iCodeFileNameFormat \
						.replace('$videoName$',self.args.vidName) \
						.replace('$frameNum$',str(currFrame).zfill(4))

					with open(iCodePath+ '/' +icFile, 'rb') as f:
						iCodesObj.append(f.read())

					fileNameToSave = f'video_segment_{str(currSegment).zfill(4)}_frame_{str(currFrame).zfill(4)}.p'
					pckFilePath = os.path.join(saveToPath, self.args.vidName , 'frames',fileNameToSave)
					with open(pckFilePath, 'wb') as f:
						pickle.dump(iCodesObj, f)

				else:
					# to pack pcodes and flows of a frame. for every frame it will be list of 4 elements, 1 pcode and 4 flows in every direction
					for tNum in range(1, totalTracks+1):
						pCodesObj = []
						pcFile = pCodeFileNameFormat \
							.replace('$videoName$',self.args.vidName) \
							.replace('$frameNum$', str(currFrame).zfill(4))

						pcTrackPath = pCodePath.replace('$trackNum$', str(tNum))
						with open(os.path.join(pcTrackPath, pcFile), 'rb') as f:
							pCodesObj.append(f.read())

						# pFlowsFileNameFormat = ['video_$videoName$_cif_$frameNum$_after_flow_x_0001.jpg', 
						for flowFileNameFormat in pFlowsFileNameFormat:
							flFile = flowFileNameFormat \
										.replace('$videoName$', self.args.vidName) \
										.replace('$frameNum$', str(currFrame).zfill(4))
							
							# logger.info('Flow file Name:{}'.format(flFile))
							with open(os.path.join(pFlowsPath, flFile), 'rb') as f:
								pCodesObj.append(f.read())
						
						fileNameToSave = f'video_track_{str(tNum).zfill(4)}_segment_{str(currSegment).zfill(4)}_frame_{str(currFrame).zfill(4)}.p'
						pckFilePath = os.path.join(saveToPath, self.args.vidName , 'frames',fileNameToSave)
						with open(pckFilePath, 'wb') as f:
							pickle.dump(iCodesObj, f)

	
parser = argparse.ArgumentParser(description="Packager")
args = parser.parse_args()

for vN in videoNames:
	args.vidName = vN
	pc = packager(args)
	pc.createFolders()
	# pc.packIcodes()
	# pc.packPcodesFlows()
	# pc.replicate(5)
	# pc.createPickledFrames()
	pc.replicateFrames(5)







