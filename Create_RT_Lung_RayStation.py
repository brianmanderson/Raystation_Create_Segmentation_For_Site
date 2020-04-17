import os
from connect import *
import time, getpass


class create_RT_Structure():
    def __init__(self,roi_name):
        self.roi_name = roi_name
        self.version_name = '_BMA_Program_4'
        try:
            self.patient_db = get_current('PatientDB')
            self.patient = get_current('Patient')
            self.case = get_current('Case')
            self.exam = get_current('Examination')
            self.MRN = self.patient.PatientID
        except:
            xxx = 1
    def ChangePatient(self, MRN):
        print('got here')
        self.MRN = MRN
        info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": self.MRN}, UseIndexService=False)
        if not info_all:
            info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": self.MRN}, UseIndexService=True)
        for info in info_all:
            if info['PatientID'] == self.MRN:
                self.patient = self.patient_db.LoadPatient(PatientInfo=info, AllowPatientUpgrade=True)
                self.MRN = self.patient.PatientID
                return None
        print('did not find a patient')
    def create_RT_Liver(self, exam):
        self.export(exam)
        if self.has_contours:
            print('Already has contours')
            return None
        self.import_data(exam)

    def export(self, exam):
        roi_name = self.roi_name
        actual_roi_name = roi_name + self.version_name
        roi_name += '_Auto_Contour'
        self.MRN = self.patient.PatientID
        self.base_path = '\\\\mymdafiles\\ou-radonc\\Raystation\\Clinical\\Auto_Contour_Sites\\'
        #if not check_any_contours(case,exam): Doesn't work the way I want it to
        self.path = os.path.join(self.base_path,'Lungs_Auto_Contour','Input_3',self.MRN)
        self.rois_in_case = []
        for roi in self.case.PatientModel.RegionsOfInterest:
            self.rois_in_case.append(roi.Name)
        self.patient.Save()
        self.has_contours = False
        if actual_roi_name in self.rois_in_case:
            if self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[actual_roi_name].HasContours():
                self.has_contours = True
                return None # Already have the contours for this patient
        self.patient.Save()
        print(self.path)
        self.Export_Dicom(exam,self.path)

    def import_data(self, exam):
        roi_name = self.roi_name
        actual_roi_name = roi_name + self.version_name
        roi_name += '_Auto_Contour'
        if actual_roi_name in self.rois_in_case:
            if self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[actual_roi_name].HasContours():
                return None # Already have the contours for this patient
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        output_path = os.path.join(self.base_path,'Lungs_Auto_Contour','Output',self.MRN,SeriesUID)
        self.cleanout_folder(output_path)
        print('Now waiting for RS to be made')
        self.import_RT = False
        self.check_folder(output_path)
        print('Import RT structure!')
        if self.import_RT:
            self.importRT(output_path)
        self.cleanout_folder(output_path)
        return None

    def Export_Dicom(self,exam, path):
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        export_path = os.path.join(path,SeriesUID)
        if not os.path.exists(export_path):
            print('making path')
            os.makedirs(export_path)
        if not os.path.exists(os.path.join(export_path,'Completed.txt')):
            fid = open(os.path.join(path,'Raystation_Export.txt'),'w+')
            fid.close()
            self.case.ScriptableDicomExport(ExportFolderPath=export_path, Examinations=[exam.Name],
                                            RtStructureSetsForExaminations=[])
            fid = open(os.path.join(export_path,'Completed.txt'),'w+')
            fid.close()
        return None
    def check_folder(self,output_path):
        print(output_path)
        while not os.path.exists(output_path):
            time.sleep(1)
        print('path exists, waiting for file')
        while not os.path.exists(os.path.join(output_path,'Completed.txt')) and not os.path.exists(os.path.join(output_path,'Failed.txt')):
            time.sleep(1)
        if os.path.exists(os.path.join(output_path,'Completed.txt')):
            self.import_RT = True
        return None
    def importRT(self,file_path):
        try:
            self.patient.ImportDicomDataFromPath(Path=file_path,CaseName=self.case.CaseName,SeriesFilter={},ImportFilters=[])
        except:
            pi = self.patient_db.QueryPatientsFromPath(Path=file_path, SearchCriterias={'PatientID': self.MRN})[0]
            studies = self.patient_db.QueryStudiesFromPath(Path=file_path,
                                                           SearchCriterias=pi)
            series = []
            for study in studies:
                series += self.patient_db.QuerySeriesFromPath(Path=file_path,
                                                              SearchCriterias=study)
            self.patient.ImportDataFromPath(Path=file_path, CaseName=self.case.CaseName,
                                            SeriesOrInstances=series, AllowMismatchingPatientID=True)
        return None

    def cleanout_folder(self,dicom_dir):
        print('Cleaning up: Removing imported DICOMs, please check output folder for result')
        if os.path.exists(dicom_dir):
            files = os.listdir(dicom_dir)
            for file in files:
                if file.find('user_') != 0:
                    os.remove(os.path.join(dicom_dir,file))
            un = getpass.getuser()
            fid = open(os.path.join(dicom_dir,'user_{}.txt'.format(un)),'w+')
            fid.close()
        return None
if __name__ == "__main__":
    class_struct = create_RT_Structure(roi_name='Lung (Left)_BMA_Program_0')
    class_struct.create_RT_Liver(class_struct.exam)