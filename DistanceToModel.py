import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import time
import math

class DistanceToModel(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "DistanceToModel" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

class DistanceToModelWidget(ScriptedLoadableModuleWidget):

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    ############################################### DistanceToModel
    distanceToModelCollapsibleButton = ctk.ctkCollapsibleButton()
    distanceToModelCollapsibleButton.text = "DistanceToModel"
    distanceToModelCollapsibleButton.collapsed = False
    self.layout.addWidget(distanceToModelCollapsibleButton)
    distanceToModelFormLayout = qt.QFormLayout(distanceToModelCollapsibleButton)

    self.modelSelector = slicer.qMRMLNodeComboBox()
    self.modelSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.modelSelector.selectNodeUponCreation = False
    self.modelSelector.addEnabled = False
    self.modelSelector.removeEnabled = False
    self.modelSelector.noneEnabled = False
    self.modelSelector.showHidden = False
    self.modelSelector.showChildNodeTypes = False
    self.modelSelector.setMRMLScene( slicer.mrmlScene )
    distanceToModelFormLayout.addRow("Select Model: ", self.modelSelector)

    self.modelTransformSelector = slicer.qMRMLNodeComboBox()
    self.modelTransformSelector.nodeTypes = ["vtkMRMLLinearTransformNode"]
    self.modelTransformSelector.selectNodeUponCreation = False
    self.modelTransformSelector.addEnabled = False
    self.modelTransformSelector.removeEnabled = False
    self.modelTransformSelector.noneEnabled = False
    self.modelTransformSelector.showHidden = False
    self.modelTransformSelector.showChildNodeTypes = False
    self.modelTransformSelector.setMRMLScene( slicer.mrmlScene )
    distanceToModelFormLayout.addRow("Select Model Transform: ", self.modelTransformSelector)
           
    self.toolTipToToolSelector = slicer.qMRMLNodeComboBox()
    self.toolTipToToolSelector.nodeTypes = ["vtkMRMLLinearTransformNode"]
    self.toolTipToToolSelector.selectNodeUponCreation = False
    self.toolTipToToolSelector.addEnabled = False
    self.toolTipToToolSelector.removeEnabled = False
    self.toolTipToToolSelector.noneEnabled = False
    self.toolTipToToolSelector.showHidden = False
    self.toolTipToToolSelector.showChildNodeTypes = False
    self.toolTipToToolSelector.setMRMLScene( slicer.mrmlScene )
    distanceToModelFormLayout.addRow("Select ToolTipToTool: ", self.toolTipToToolSelector)
    
    self.toolToReferenceSelector = slicer.qMRMLNodeComboBox()
    self.toolToReferenceSelector.nodeTypes = ["vtkMRMLLinearTransformNode"]
    self.toolToReferenceSelector.selectNodeUponCreation = False
    self.toolToReferenceSelector.addEnabled = False
    self.toolToReferenceSelector.removeEnabled = False
    self.toolToReferenceSelector.noneEnabled = False
    self.toolToReferenceSelector.showHidden = False
    self.toolToReferenceSelector.showChildNodeTypes = False
    self.toolToReferenceSelector.setMRMLScene( slicer.mrmlScene )
    distanceToModelFormLayout.addRow("Select ToolToReference: ", self.toolToReferenceSelector)
    
    self.calculateDistanceButton = qt.QPushButton("Calculate Distance")
    self.calculateDistanceButton.enabled = False
    self.calculateDistanceButton.checkable = True
    distanceToModelFormLayout.addRow(self.calculateDistanceButton)   
    
    ############################################### Connections
    self.modelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.modelTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.toolTipToToolSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.toolToReferenceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.calculateDistanceButton.connect('clicked(bool)', self.onCalculateDistanceClicked)
    
    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

    # Members
    self.distanceToModelLogic = None
    
  def onSelect(self):
    self.calculateDistanceButton.enabled = self.modelSelector.currentNode() and self.modelTransformSelector.currentNode() and self.toolTipToToolSelector.currentNode() and self.toolToReferenceSelector.currentNode() 
      
  def onCalculateDistanceClicked(self):
    if self.calculateDistanceButton.checked:    
      if not self.distanceToModelLogic:
        self.distanceToModelLogic = DistanceToModelLogic(self.modelSelector.currentNode())
      self.distanceToModelLogic.SetMembers(self.modelSelector.currentNode(), self.modelTransformSelector.currentNode(), self.toolTipToToolSelector.currentNode(), self.toolToReferenceSelector.currentNode())
      self.distanceToModelLogic.addCalculateDistanceObserver()  
    elif not self.calculateDistanceButton.checked:        
      self.distanceToModelLogic.removeCalculateDistanceObserver()  
         
class DistanceToModelLogic(ScriptedLoadableModuleLogic):

  def __init__(self, modelNode):
    self.modelNode = modelNode
    self.toolTipToTool = None
    self.toolToReference = None
    self.modelTransform = None
  
    self.transformedModel = slicer.util.getNode('Transformed Model')
    if not self.transformedModel:
      self.transformedModel = slicer.vtkMRMLModelNode()
      self.transformedModel.SetName('Transformed Model')
      self.transformedModel.SetAndObservePolyData(self.modelNode.GetPolyData())     
      modelDisplay = slicer.vtkMRMLModelDisplayNode()
      modelDisplay.SetSliceIntersectionVisibility(True)
      modelDisplay.SetColor(0,1,0)
      slicer.mrmlScene.AddNode(modelDisplay)      
      self.transformedModel.SetAndObserveDisplayNodeID(modelDisplay.GetID())      
      slicer.mrmlScene.AddNode(self.transformedModel)
      self.transformedModel.SetDisplayVisibility(False)     

    self.closestFiducial = slicer.util.getNode('CP')
    if not self.closestFiducial:
      self.closestFiducial = slicer.vtkMRMLMarkupsFiducialNode()  
      self.closestFiducial.SetName('CP')
      self.closestFiducial.AddFiducial(0, 0, 0)
      self.closestFiducial.SetNthFiducialLabel(0, '')
      slicer.mrmlScene.AddNode(self.closestFiducial)
      self.closestFiducial.SetDisplayVisibility(False)
      self.closestFiducial.GetDisplayNode().SetGlyphScale(3.0)
      self.closestFiducial.GetDisplayNode().SetGlyphType(4) # ThickCross2D
      self.closestFiducial.GetDisplayNode().SetSelectedColor(0,0,1)

    self.tipFiducial = slicer.util.getNode('Tip')
    if not self.tipFiducial:
      self.tipFiducial = slicer.vtkMRMLMarkupsFiducialNode()  
      self.tipFiducial.SetName('Tip')
      self.tipFiducial.AddFiducial(0, 0, 0)
      self.tipFiducial.SetNthFiducialLabel(0, '')
      slicer.mrmlScene.AddNode(self.tipFiducial)
      self.tipFiducial.SetDisplayVisibility(True)
      self.tipFiducial.GetDisplayNode().SetGlyphType(1) # Vertex2D
      self.tipFiducial.GetDisplayNode().SetTextScale(1.3)
      self.tipFiducial.GetDisplayNode().SetSelectedColor(1,1,1)
      
    self.line = slicer.util.getNode('Line')
    if not self.line:
      self.line = slicer.vtkMRMLModelNode()
      self.line.SetName('Line')
      linePolyData = vtk.vtkPolyData()
      self.line.SetAndObservePolyData(linePolyData)      
      modelDisplay = slicer.vtkMRMLModelDisplayNode()
      modelDisplay.SetSliceIntersectionVisibility(True)
      modelDisplay.SetColor(0,1,0)
      slicer.mrmlScene.AddNode(modelDisplay)      
      self.line.SetAndObserveDisplayNodeID(modelDisplay.GetID())      
      slicer.mrmlScene.AddNode(self.line)
      
    # VTK objects
    self.transformPolyDataFilter = vtk.vtkTransformPolyDataFilter()
    self.cellLocator = vtk.vtkCellLocator()
    
    # 3D View
    threeDWidget = slicer.app.layoutManager().threeDWidget(0)
    self.threeDView = threeDWidget.threeDView()
    
    self.callbackObserverTag = -1

  def SetMembers(self, modelNode, modelTransform, toolTipToTool, toolToReference):
    self.modelNode = modelNode
    self.toolTipToTool = toolTipToTool
    self.toolToReference = toolToReference
    self.modelTransform = modelTransform

  def addCalculateDistanceObserver(self):
    if self.callbackObserverTag == -1:
      self.tipFiducial.SetAndObserveTransformNodeID(self.toolTipToTool.GetID())
      self.callbackObserverTag = self.toolToReference.AddObserver('ModifiedEvent', self.calculateCallback) # slicer.vtkMRMLMarkupsNode.MarkupAddedEvent
      logging.info('addCalculateDistanceObserver')
    
  def removeCalculateDistanceObserver(self):
    if self.callbackObserverTag != -1:
      self.toolToReference.RemoveObserver(self.callbackObserverTag)
      self.callbackObserverTag = -1
      logging.info('removeCalculateDistanceObserver')
      
  def calculateCallback(self, transformNode, event=None):
    self.transformPolyData(self.modelTransform)
    self.buildLocator(self.transformedModel)
    self.calculateDistance()
    
  def buildLocator(self, modelNode):   
    self.cellLocator.SetDataSet(modelNode.GetPolyData())
    self.cellLocator.BuildLocator()
    
  def calculateDistance(self):
    point = [0.0,0.0,0.0]
    closestPoint = [0.0, 0.0, 0.0]
    
    m = vtk.vtkMatrix4x4()
    self.toolTipToTool.GetMatrixTransformToWorld(m)
    point[0] = m.GetElement(0, 3)
    point[1] = m.GetElement(1, 3)
    point[2] = m.GetElement(2, 3)        
    
    distanceSquared = vtk.mutable(0.0) 
    subId = vtk.mutable(0) 
    cellId = vtk.mutable(0) 
    cell = vtk.vtkGenericCell()
    
    self.cellLocator.FindClosestPoint(point, closestPoint, cell, cellId, subId, distanceSquared);
    distance = math.sqrt(distanceSquared)
          
    self.closestFiducial.SetNthFiducialPosition(0,  closestPoint[0], closestPoint[1], closestPoint[2])
    self.closestFiducial.SetDisplayVisibility(True)
    
    self.drawLineBetweenPoints(point, closestPoint)
    
    self.tipFiducial.SetNthFiducialLabel(0, '     %.0f' % distance + 'mm')    
    
  def drawLineBetweenPoints(self, point1, point2):        
    # Create a vtkPoints object and store the points in it
    points = vtk.vtkPoints()
    points.InsertNextPoint(point1)
    points.InsertNextPoint(point2)

    # Create line
    line = vtk.vtkLine()
    line.GetPointIds().SetId(0,0) 
    line.GetPointIds().SetId(1,1)
    lineCellArray = vtk.vtkCellArray()
    lineCellArray.InsertNextCell(line)
    
    # Update model data
    self.line.GetPolyData().SetPoints(points)
    self.line.GetPolyData().SetLines(lineCellArray)
    
  def transformPolyData(self, transformNode):
    t = vtk.vtkGeneralTransform()
    transformNode.GetTransformToWorld(t)
    
    self.transformPolyDataFilter.SetTransform(t)
    self.transformPolyDataFilter.SetInputData(self.modelNode.GetPolyData())
    self.transformPolyDataFilter.Update()

    self.transformedModel.SetAndObservePolyData(self.transformPolyDataFilter.GetOutput())    
    
class DistanceToModelTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_DistanceToModel1()

  def test_DistanceToModel1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = DistanceToModelLogic()
    #self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
