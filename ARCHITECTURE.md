# Architecture

Application is a single window that contains two panels:
1. The overview panel takes up 1/3 of the window and contains the following:
   1. Output parent path
   2. Output directory name
   3. Several checkboxes to toggle different settings
2. The devices panel takes up 2/3 of the window and contains the following:
   1. Buttons to do various operations, for example "Dump Logs". When this button is pressed, settings and paths are taken into account from the overview panel.

## Heirarchy

Current heirarchy is as follows:

- \__main__
  - Creates AppController
    - Creates QApplication
    - Creates SettingsModel
    - Creates SettingsController(view=None, model=SettingsModel)
    - Creates MainWindowQMainWindow(controller=SettingsController)
      - Creates OverviewView, DevicesView
      - Creates OverviewModel, DevicesModel
      - Creates OverviewController(view=OverviewView, model=OverviewModel), DevicesController(view=DevicesView, model=DevicesModel)
      - I still need something to link the two -> For example, there is an input box on the OverviewView which the DevicesController probably needs access to at some point
  - Calls AppController.run()
    - Calls MainWindowQMainWindow.show()
    - Calls QApplication.exec()

Corrected heirarchy:
- \__main__
  - Creates AppController
    - Creates QApplication
    - Creates OverviewModel, DevicesModel
    - Creates OverviewView, DevicesView
    - Creates MainWindow(overview=OverviewView, devices=DevicesView)
    - Creates OverviewController(view=OverviewView, model=OverviewModel)
    - Creates DevicesController(view=DevicesView, model=DevicesModel, settings=OverviewModel)
  - Calls AppController.run()
    - Calls MainWindowQMainWindow.show()
    - Calls QApplication.exec()
