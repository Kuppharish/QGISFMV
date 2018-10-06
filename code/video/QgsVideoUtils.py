from QGIS_FMV.utils.QgsFmvUtils import (GetImageWidth,
                                        GetImageHeight)

from QGIS_FMV.utils.QgsFmvUtils import (GetSensor,
                                        GetLine3DIntersectionWithDEM,
                                        GetFrameCenter,
                                        hasElevationModel,
                                        GetGCPGeoTransform)
try:
    from pydevd import *
except ImportError:
    None


class VideoUtils(object):

    @staticmethod
    def GetNormalizedWidth(surface):
        return surface.height(
        ) * (GetImageWidth() / GetImageHeight())

    @staticmethod
    def GetInverseMatrix(x, y, gt, surface):
        ''' inverse matrix transformation (lon-lat to video units x,y) '''
        transf = (~gt)([x, y])
        scr_x = (transf[0] / VideoUtils.GetXRatio(surface)) + \
            VideoUtils.GetXBlackZone(surface)
        scr_y = (transf[1] / VideoUtils.GetYRatio(surface)) + \
            VideoUtils.GetYBlackZone(surface)
        return scr_x, scr_y

    @staticmethod
    def GetXRatio(surface):
        ''' ratio between event.x() and real image width on screen. '''
        return GetImageWidth() / (surface.width() - (2 * VideoUtils.GetXBlackZone(surface)))

    @staticmethod
    def GetYRatio(surface):
        ''' ratio between event.y() and real image height on screen. '''
        return GetImageHeight() / (surface.height() - (2 * VideoUtils.GetYBlackZone(surface)))

    @staticmethod
    def GetXBlackZone(surface):
        ''' Return is X in black screen on video '''
        x = 0.0
        if (surface.width() / surface.height()) > (GetImageWidth() / GetImageHeight()):
            x = (surface.width() -
                 (VideoUtils.GetNormalizedWidth(surface))) / 2.0
        return x

    @staticmethod
    def GetNormalizedHeight(surface):
        return surface.width()

    @staticmethod
    def GetYBlackZone(surface):
        ''' Return is Y in black screen on video '''
        y = 0.0
        if (surface.width() / surface.height()) < (GetImageWidth() / GetImageHeight()):
            y = (surface.height() -
                 (VideoUtils.GetNormalizedHeight(surface))) / 2.0
        return y

    @staticmethod
    def IsPointOnScreen(x, y, surface):
        ''' determines if a clicked point lands on the image (False if lands on the
            black borders or outside)
         '''
        res = True
        if x > (VideoUtils.GetNormalizedWidth(surface) + VideoUtils.GetXBlackZone(surface)) or x < VideoUtils.GetXBlackZone(surface):
            res = False
        if y > (VideoUtils.GetNormalizedHeight(surface) + VideoUtils.GetYBlackZone(surface)) or y < VideoUtils.GetYBlackZone(surface):
            res = False
        return res

    @staticmethod
    def GetTransf(event, surface):
        ''' Return video coordinates to map coordinates '''
        gt = GetGCPGeoTransform()
        return gt([(event.x() - VideoUtils.GetXBlackZone(surface)) * VideoUtils.GetXRatio(surface), (event.y() - VideoUtils.GetYBlackZone(surface)) * VideoUtils.GetYRatio(surface)])

    @staticmethod
    def GetPointCommonCoords(event, surface):
        ''' Common functon for get coordinates on mousepressed '''
        transf = VideoUtils.GetTransf(event, surface)
        targetAlt = GetFrameCenter()[2]

        Longitude = float(round(transf[1], 5))
        Latitude = float(round(transf[0], 5))
        Altitude = float(round(targetAlt, 0))

        if hasElevationModel():
            sensor = GetSensor()
            target = [transf[0], transf[1], targetAlt]
            projPt = GetLine3DIntersectionWithDEM(sensor, target)
            if projPt:
                Longitude = float(round(projPt[1], 5))
                Latitude = float(round(projPt[0], 5))
                Altitude = float(round(projPt[2], 0))
        return Longitude, Latitude, Altitude
