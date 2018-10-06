# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QRect, QPoint, QBasicTimer, QSize
from PyQt5.QtGui import (QImage,
                         QPalette,
                         QPixmap,
                         QPainter,
                         QRegion,
                         QColor,
                         QBrush,
                         QCursor,
                         QTransform)

from PyQt5.QtMultimedia import (QAbstractVideoBuffer,
                                QVideoFrame,
                                QAbstractVideoSurface,
                                QVideoSurfaceFormat)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import QSizePolicy, QWidget, QRubberBand

from QGIS_FMV.utils.QgsFmvUtils import (SetImageSize,
                                        convertQImageToMat,
                                        GetGCPGeoTransform,
                                        hasElevationModel,
                                        GetImageHeight)

from QGIS_FMV.utils.QgsFmvLayers import AddDrawPointOnMap, AddDrawLineOnMap, AddDrawPolygonOnMap

from QGIS_FMV.utils.QgsUtils import QgsUtils as qgsu
from QGIS_FMV.video.QgsVideoFilters import VideoFilters as filter
from QGIS_FMV.video.QgsVideoUtils import VideoUtils as vut
from QGIS_FMV.player.QgsFmvDrawToolBar import DrawToolBar as draw
from qgis.gui import QgsRubberBand
from qgis.utils import iface
from qgis.core import Qgis as QGis, QgsPointXY

try:
    from pydevd import *
except ImportError:
    None

try:
    import cv2
except ImportError:
    None


class InteractionState(object):
    """ Interaction Video Player Class """

    def __init__(self):
        self.pointDrawer = False
        self.ruler = False
        self.lineDrawer = False
        self.polygonDrawer = False
        self.magnifier = False
        self.objectTracking = False
        self.censure = False

    def clear(self):
        self.__init__()


class FilterState(object):
    """ Filters State Video Player Class """

    def __init__(self):
        self.contrastFilter = False
        self.monoFilter = False
        self.MirroredHFilter = False
        self.edgeDetectionFilter = False
        self.grayColorFilter = False
        self.invertColorFilter = False

    def clear(self):
        self.__init__()


class VideoWidgetSurface(QAbstractVideoSurface):

    def __init__(self, widget, parent=None):
        ''' Constructor '''
        super(VideoWidgetSurface, self).__init__(parent)

        self.widget = widget
        self.imageFormat = QImage.Format_Invalid
        self.image = None

    def supportedPixelFormats(self, handleType=QAbstractVideoBuffer.NoHandle):
        ''' Available Frames Format '''
        formats = [QVideoFrame.PixelFormat()]
        if handleType == QAbstractVideoBuffer.NoHandle:
            for f in [QVideoFrame.Format_RGB32,
                      QVideoFrame.Format_ARGB32,
                      QVideoFrame.Format_ARGB32_Premultiplied,
                      QVideoFrame.Format_RGB565,
                      QVideoFrame.Format_RGB555
                      ]:
                formats.append(f)
        return formats

    def isFormatSupported(self, _format):
        ''' Check if is supported VideFrame format '''
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(
            _format.pixelFormat())
        size = _format.frameSize()
        _bool = False
        if (imageFormat != QImage.Format_Invalid and not
            size.isEmpty() and
                _format.handleType() == QAbstractVideoBuffer.NoHandle):
            _bool = True
        return _bool

    def start(self, _format):
        ''' Start QAbstractVideoSurface '''
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(
            _format.pixelFormat())
        size = _format.frameSize()
        if (imageFormat != QImage.Format_Invalid and not size.isEmpty()):
            self.sourceRect = _format.viewport()
            QAbstractVideoSurface.start(self, _format)
            self.imageFormat = imageFormat
            self.imageSize = size
            self.widget.updateGeometry()
            self.updateVideoRect()
            return True
        else:
            return False

    def stop(self):
        ''' Stop Video '''
        self.currentFrame = QVideoFrame()
        self.targetRect = QRect()
        QAbstractVideoSurface.stop(self)
        self.widget.update()

    def present(self, frame):
        ''' Present Frame '''
        if (self.surfaceFormat().pixelFormat() != frame.pixelFormat() or
                self.surfaceFormat().frameSize() != frame.size()):
            self.setError(QAbstractVideoSurface.IncorrectFormatError)
            self.stop()
            return False
        else:
            self.currentFrame = frame
            self.widget.repaint(self.targetRect)
            return True

    def videoRect(self):
        ''' Get Video Rectangle '''
        return self.targetRect

    def GetsourceRect(self):
        ''' Get Source Rectangle '''
        return self.sourceRect

    def updateVideoRect(self):
        ''' Update video rectangle '''
        size = self.surfaceFormat().sizeHint()
        size.scale(self.widget.size().boundedTo(size), Qt.KeepAspectRatio)
        self.targetRect = QRect(QPoint(0, 0), size)
        self.targetRect.moveCenter(self.widget.rect().center())

    def paint(self):
        ''' Paint Frame'''
        if (self.currentFrame.map(QAbstractVideoBuffer.ReadOnly)):
            #oldTransform = painter.transform()
            None

#         if (self.surfaceFormat().scanLineDirection() == QVideoSurfaceFormat.BottomToTop):
#             None
            #painter.scale(1, -1)
            #painter.translate(0, -self.widget.height())

        self.image = QImage(self.currentFrame.bits(),
                            self.currentFrame.width(),
                            self.currentFrame.height(),
                            self.currentFrame.bytesPerLine(),
                            self.imageFormat
                            )

        if self.widget._filterSatate.grayColorFilter:
            self.image = filter.GrayFilter(self.image)

        if self.widget._filterSatate.MirroredHFilter:
            self.image = filter.MirrredFilter(self.image)

        if self.widget._filterSatate.monoFilter:
            self.image = filter.MonoFilter(self.image)

        if self.widget._filterSatate.edgeDetectionFilter:
            self.image = filter.EdgeFilter(self.image)

        if self.widget._filterSatate.contrastFilter:
            self.image = filter.AutoContrastFilter(self.image)

        if self.widget._filterSatate.invertColorFilter:
            self.image.invertPixels()

#         painter.drawImage(self.targetRect, self.image, self.sourceRect)
# 
#         if self._interaction.objectTracking and self.widget._isinit:
#             frame = convertQImageToMat(self.image)
#             # Update tracker
#             ok, bbox = self.widget.tracker.update(frame)
#             # Draw bounding box
#             if ok:
#                 #                 qgsu.showUserAndLogMessage(
#                 #                     "bbox : ", str(bbox), level=QGis.Warning)
#                 painter.setPen(Qt.blue)
#                 painter.drawRect(QRect(int(bbox[0]), int(
#                     bbox[1]), int(bbox[2]), int(bbox[3])))
#             else:
#                 qgsu.showUserAndLogMessage(
#                     "Tracking failure detected ", "", level=QGis.Warning)
# 
#         painter.setTransform(oldTransform)
        self.currentFrame.unmap()
        return self.image


class VideoWidget(QVideoWidget):

    def __init__(self, parent=None):
        ''' Constructor '''
        super(VideoWidget, self).__init__(parent)
        self.surface = VideoWidgetSurface(self)
        self._image = None
        self.Tracking_RubberBand = QRubberBand(QRubberBand.Rectangle, self)

        pal = QPalette()
        pal.setBrush(QPalette.Highlight, QBrush(QColor(Qt.blue)))
        self.Tracking_RubberBand.setPalette(pal)
        self.var_currentMouseMoveEvent = None

        self._interaction = InteractionState()
        self._filterSatate = FilterState()

        self.setUpdatesEnabled(True)
        self.snapped = False
        self.zoomed = False
        self._isinit = False
        self.gt = None
        self.pointIndex = 1

        self.poly_coordinates, self.drawPtPos, self.drawLines, self.drawRuler, self.drawPolygon = [], [], [], [], []
        self.poly_RubberBand = QgsRubberBand(
            iface.mapCanvas(), True)  # Polygon type
        # set rubber band style
        color = QColor(176, 255, 128)
        self.poly_RubberBand.setColor(color)
        color.setAlpha(190)
        self.poly_RubberBand.setStrokeColor(color)
        self.poly_RubberBand.setWidth(3)

        self.parent = parent.parent()

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_PaintOnScreen)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        palette = self.palette()
        palette.setColor(QPalette.Background, Qt.black)
        self.setPalette(palette)
        self.setSizePolicy(QSizePolicy.MinimumExpanding,
                           QSizePolicy.MinimumExpanding)

        self.offset, self.origin, self.pressPos, self.dragPos = QPoint(
        ), QPoint(), QPoint(), QPoint()
        self.tapTimer = QBasicTimer()
        self.zoomPixmap, self.maskPixmap = QPixmap(), QPixmap()

    def ResetDrawRuler(self):
        ''' Resets DrawRuler Points List '''
        self.drawRuler = []

    def currentMouseMoveEvent(self, event):
        self.var_currentMouseMoveEvent = event

    def keyPressEvent(self, event):
        ''' Exit fullscreen '''
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.setFullScreen(False)
            event.accept()
        elif event.key() == Qt.Key_Enter and event.modifiers() & Qt.Key_Alt:
            self.setFullScreen(not self.isFullScreen())
            event.accept()
        else:
            super(VideoWidget, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        :type event: QMouseEvent
        :param event:
        :return:
        """
        if GetImageHeight() == 0:
            return

        if(not vut.IsPointOnScreen(event.x(), event.y(), self)):
            return

        if self.gt is not None and self._interaction.lineDrawer:
            self.drawLines.append([None, None, None])
            self.UpdateSurface()
            return
        if self.gt is not None and self._interaction.ruler:
            self.drawRuler.append([None, None, None])
            self.UpdateSurface()
            return
        if self.gt is not None and self._interaction.polygonDrawer:
            self.drawPolygon.append([None, None, None])

            AddDrawPolygonOnMap(self.poly_coordinates)

            # Empty RubberBand
            for _ in range(self.poly_RubberBand.numberOfVertices()):
                self.poly_RubberBand.removeLastPoint()
            # Empty List
            self.poly_coordinates = []
            self.UpdateSurface()
            return

        self.setFullScreen(not self.isFullScreen())
        event.accept()

    def videoSurface(self):
        ''' Return video Surface '''
        return self.surface

    def UpdateSurface(self):
        ''' Update Video Surface '''
        self.surface.widget.update()

    def sizeHint(self):
        ''' This property holds the recommended size for the widget '''
        return self.surface.surfaceFormat().sizeHint()

    def GetCurrentFrame(self):
        ''' Return current frame QImage '''
        return self.surface.image

    def GetCurrentFrameImage(self):
        return self._image

    def SetInvertColor(self, value):
        ''' Set Invert color filter '''
        self._filterSatate.invertColorFilter = value

    def SetObjectTracking(self, value):
        ''' Set Object Tracking '''
        self._interaction.objectTracking = value

    def SetRuler(self, value):
        ''' Set Ruler '''
        self._interaction.ruler = value

    def SetCensure(self, value):
        ''' Set Censure Video Parts '''
        self._interaction.censure = value

    def SetGray(self, value):
        ''' Set gray scale '''
        self._filterSatate.grayColorFilter = value

    def SetMirrorH(self, value):
        ''' Set Horizontal Mirror '''
        self._filterSatate.MirroredHFilter = value

    def SetEdgeDetection(self, value):
        ''' Set Canny Edge filter '''
        self._filterSatate.edgeDetectionFilter = value

    def SetAutoContrastFilter(self, value):
        ''' Set Automatic Contrast filter '''
        self._filterSatate.contrastFilter = value

    def SetMonoFilter(self, value):
        ''' Set mono filter '''
        self._filterSatate.monoFilter = value

    def RestoreFilters(self):
        ''' Remove and restore all video filters '''
        self._filterSatate.clear()

    def RestoreDrawer(self):
        ''' Remove and restore all Drawer Options '''
        self._interaction.clear()

    def paintEvent(self, event):
        ''' Paint Event '''
        self.gt = GetGCPGeoTransform()

        self.painter = QPainter(self)
        self.painter.setRenderHint(QPainter.HighQualityAntialiasing)
        if (self.surface.isActive()):
            videoRect = self.surface.videoRect()
            if not videoRect.contains(event.rect()):
                region = event.region()
                region.subtracted(QRegion(videoRect))
                brush = self.palette().window()
                for rect in region.rects():
                    self.painter.fillRect(rect, brush)

            try:
                self._image = self.surface.paint()
            except Exception:
                None
        else:
            self.painter.fillRect(event.rect(), self.palette().window())

        if self._image is not None:

            SetImageSize(self._image.width(),
                         self._image.height())
 
            self.painter.scale(1, -1)
            self.painter.translate(0, -self.height())
            transform = QTransform()
            scale = min(self.width()/self._image.width(), self.height()/self._image.height())
            transform.translate((self.width() - self._image.width()*scale)/2, (self.height() - self._image.height()*scale)/2)
            transform.scale(scale, scale)

            inverse_transform, invertible = transform.inverted()
            rect = inverse_transform.mapRect(event.rect()).adjusted(-1, -1, 1, 1).intersected(self._image.rect())
            self.painter.setTransform(transform)
            self.painter.drawImage(rect, self._image, rect)

        # Draw On Video
        draw.drawOnVideo(self.drawPtPos, self.drawLines, self.drawPolygon,
                         self.drawRuler, self.painter, self, self.gt)

        # Magnifier Glass
        if self.zoomed and self._interaction.magnifier:
            draw.drawMagnifierOnVideo(self.width(), self.height(
            ), self.maskPixmap, self.dragPos, self.zoomPixmap, self.surface, self.painter, self.offset)

        self.painter.end()
        return

    def resizeEvent(self, event):
        """
        :type event: QMouseEvent
        :param event:
        :return:
        """
        QWidget.resizeEvent(self, event)
        self.zoomed = False
        self.surface.updateVideoRect()

    def mouseMoveEvent(self, event):
        """
        :type event: QMouseEvent
        :param event:
        :return:
        """
        if GetImageHeight() == 0:
            return

        # check if the point  is on picture (not in black borders)
        if(not vut.IsPointOnScreen(event.x(), event.y(), self)):
            return

        if self._interaction.pointDrawer or self._interaction.polygonDrawer or self._interaction.lineDrawer or self._interaction.ruler:
            self.setCursor(QCursor(Qt.CrossCursor))

        # Cursor Coordinates
        if self.gt is not None:

            Longitude, Latitude, Altitude = vut.GetPointCommonCoords(
                event, self)

            txt = "<span style='font-size:10pt; font-weight:bold;'>Lon :</span>"
            txt += "<span style='font-size:9pt; font-weight:normal;'>" + \
                ("%.3f" % Longitude) + "</span>"
            txt += "<span style='font-size:10pt; font-weight:bold;'> Lat :</span>"
            txt += "<span style='font-size:9pt; font-weight:normal;'>" + \
                ("%.3f" % Latitude) + "</span>"

            if hasElevationModel():
                txt += "<span style='font-size:10pt; font-weight:bold;'> Alt :</span>"
                txt += "<span style='font-size:9pt; font-weight:normal;'>" + \
                    ("%.0f" % Altitude) + "</span>"
            else:
                txt += "<span style='font-size:10pt; font-weight:bold;'> Alt :</span>"
                txt += "<span style='font-size:9pt; font-weight:normal;'>-</span>"

            self.parent.lb_cursor_coord.setText(txt)

        else:
            self.parent.lb_cursor_coord.setText("<span style='font-size:10pt; font-weight:bold;'>Lon :</span>" +
                                                "<span style='font-size:9pt; font-weight:normal;'>-</span>" +
                                                "<span style='font-size:10pt; font-weight:bold;'> Lat :</span>" +
                                                "<span style='font-size:9pt; font-weight:normal;'>-</span>" +
                                                "<span style='font-size:10pt; font-weight:bold;'> Alt :</span>" +
                                                "<span style='font-size:9pt; font-weight:normal;'>-</span>")

        if not event.buttons():
            return

        if not self.Tracking_RubberBand.isHidden():
            self.Tracking_RubberBand.setGeometry(
                QRect(self.origin, event.pos()).normalized())

        if not self.zoomed:
            delta = event.pos() - self.pressPos
            if not self.snapped:
                self.pressPos = event.pos()
                self.pan(delta)
                self.tapTimer.stop()
                return
            else:
                threshold = 10
                self.snapped &= delta.x() < threshold
                self.snapped &= delta.y() < threshold
                self.snapped &= delta.x() > -threshold
                self.snapped &= delta.y() > -threshold

        else:
            self.dragPos = event.pos()
            self.surface.updateVideoRect()

    def pan(self, delta):
        """ Pan Action (Magnifier method)"""
        self.offset += delta
        self.surface.updateVideoRect()

    def timerEvent(self, _):
        """ Time Event (Magnifier method)"""
        if not self.zoomed:
            self.activateMagnifier()
        self.surface.updateVideoRect()

    def mousePressEvent(self, event):
        """
        :type event: QMouseEvent
        :param event:
        :return:
        """
        if GetImageHeight() == 0:
            return

        if event.button() == Qt.LeftButton:
            self.snapped = True
            self.pressPos = self.dragPos = event.pos()
            self.tapTimer.stop()
            self.tapTimer.start(100, self)

            if(not vut.IsPointOnScreen(event.x(), event.y(), self)):
                self.UpdateSurface()
                return

            # point drawer
            if self.gt is not None and self._interaction.pointDrawer:
                
                Longitude, Latitude, Altitude = vut.GetPointCommonCoords(
                    event, self)

                AddDrawPointOnMap(self.pointIndex, Longitude,
                                  Latitude, Altitude)
                self.pointIndex += 1

                self.drawPtPos.append([Longitude, Latitude, Altitude])

            # polygon drawer
            if self.gt is not None and self._interaction.polygonDrawer:
                Longitude, Latitude, Altitude = vut.GetPointCommonCoords(
                    event, self.surface)
                self.poly_RubberBand.addPoint(QgsPointXY(Longitude, Latitude))
                self.poly_coordinates.extend(QgsPointXY(Longitude, Latitude))
                self.drawPolygon.append([Longitude, Latitude, Altitude])

            # line drawer
            if self.gt is not None and self._interaction.lineDrawer:
                Longitude, Latitude, Altitude = vut.GetPointCommonCoords(
                    event, self.surface)

                AddDrawLineOnMap(Longitude, Latitude, Altitude, self.drawLines)

                self.drawLines.append([Longitude, Latitude, Altitude])

            if self._interaction.objectTracking:
                self.origin = event.pos()
                self.Tracking_RubberBand.setGeometry(
                    QRect(self.origin, QSize()))
                self.Tracking_RubberBand.show()

            # Ruler drawer
            if self.gt is not None and self._interaction.ruler:
                Longitude, Latitude, Altitude = vut.GetPointCommonCoords(
                    event, self.surface)
                self.drawRuler.append([Longitude, Latitude, Altitude])

        # if not called, the paint event is not triggered.
        self.UpdateSurface()

    def activateMagnifier(self):
        """ Activate Magnifier Glass """
        self.zoomed = True
        self.tapTimer.stop()
        self.surface.updateVideoRect()

    def SetMagnifier(self, value):
        """ Set Magnifier Glass """
        self._interaction.magnifier = value

    def SetPointDrawer(self, value):
        """ Set Point Drawer """
        self._interaction.pointDrawer = value

    def SetLineDrawer(self, value):
        """ Set Line Drawer """
        self._interaction.lineDrawer = value

    def SetPolygonDrawer(self, value):
        """ Set Polygon Drawer """
        self._interaction.polygonDrawer = value

    def mouseReleaseEvent(self, _):
        """
        :type event: QMouseEvent
        :param event:
        :return:
        """
        if self._interaction.objectTracking:
            geom = self.Tracking_RubberBand.geometry()
            bbox = (geom.x(), geom.y(), geom.width(), geom.height())
            frame = convertQImageToMat(self.GetCurrentFrame())
            self.Tracking_RubberBand.hide()
            self.tracker = cv2.TrackerBoosting_create()
            self.tracker.clear()
            ok = self.tracker.init(frame, bbox)
            if ok:
                self._isinit = True
            else:
                self._isinit = False

    def leaveEvent(self, _):
        self.parent.lb_cursor_coord.setText("")
        self.setCursor(QCursor(Qt.ArrowCursor))
