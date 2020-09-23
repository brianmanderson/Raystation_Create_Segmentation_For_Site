import os
from connect import *
from connect import set_progress
import time, getpass


class create_RT_Structure():
    def __init__(self, roi_name):
        self.roi_name = roi_name
        self.version_name = '_BMA_Program_4'
        self.base_path = '\\\\mymdafiles\\ou-radonc\\Raystation\\Clinical\\Auto_Contour_Sites\\'
        try:
            os.listdir(self.base_path)
        except:
            self.base_path = '\\\\mymdafiles\\ou-radonc\\Raystation\\Research\\Auto_Contour_Sites\\'
        self.has_contours = False
        try:
            self.patient_db = get_current('PatientDB')
            self.patient = get_current('Patient')
            self.case = get_current('Case')
            self.exam = get_current('Examination')
            self.path = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Input_3', self.patient.PatientID)
        except:
            xxx = 1

    def ChangePatient(self, MRN):
        print('got here')
        info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": MRN}, UseIndexService=False)
        if not info_all:
            info_all = self.patient_db.QueryPatientInfo(Filter={"PatientID": MRN}, UseIndexService=True)
        for info in info_all:
            if info['PatientID'] == MRN:
                self.patient = self.patient_db.LoadPatient(PatientInfo=info, AllowPatientUpgrade=True)
                self.path = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Input_3',
                                         self.patient.PatientID)
                return None
        print('did not find a patient')

    def get_rois_in_case(self):
        self.rois_in_case = []
        for roi in self.case.PatientModel.RegionsOfInterest:
            self.rois_in_case.append(roi.Name)

    def create_RT_Liver(self, exam):
        self.export(exam)
        if not self.has_contours:
            self.import_data(exam)
        else:
            print('Already has contours')
            return None

    def check_has_contours(self, exam):
        set_progress('Checking to see if {} already has contours'.format(self.roi_name + self.version_name))
        self.get_rois_in_case()
        self.has_contours = False
        if self.roi_name + self.version_name in self.rois_in_case:
            if self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[self.roi_name +
                                                                             self.version_name].HasContours():
                self.has_contours = True
                return True  # Already have the contours for this patient
        return False

    def export(self, exam):
        if not self.check_has_contours(exam):
            self.patient.Save()
            print(self.path)
            self.Export_Dicom(exam)

    def import_data(self, exam):
        if self.roi_name + self.version_name in self.rois_in_case:
            if self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[self.roi_name +
                                                                             self.version_name].HasContours():
                return None  # Already have the contours for this patient
        self.cleanout_folder(exam)
        print('Now waiting for RS to be made')
        self.import_RT = False
        self.check_folder(exam)
        print('Import RT structure!')
        if self.import_RT:
            self.importRT(exam)
        self.cleanout_folder(exam)
        return None

    def Export_Dicom(self, exam):
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        export_path = os.path.join(self.path, SeriesUID)
        if not os.path.exists(export_path):
            print('making path')
            os.makedirs(export_path)
        set_progress('Exporting dicom series')
        if not os.path.exists(os.path.join(export_path, 'Completed.txt')):
            self.case.ScriptableDicomExport(ExportFolderPath=export_path, Examinations=[exam.Name],
                                            RtStructureSetsForExaminations=[])
            fid = open(os.path.join(export_path, 'Completed.txt'), 'w+')
            fid.close()
        set_progress('Finished exporting, waiting in queue')
        return None

    def update_progress(self, output_path):
        files = [i for i in os.listdir(output_path) if i.startswith('Status')]
        for file in files:
            set_progress('{}'.format(file.split('Status_')[-1].split('.txt')[0]))

    def check_folder(self, exam):
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        output_path = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Output',
                                   self.patient.PatientID, SeriesUID)
        print(output_path)
        while not os.path.exists(output_path):
            time.sleep(1)
        print('path exists, waiting for file')
        while not os.path.exists(os.path.join(output_path, 'Completed.txt')) and not os.path.exists(
                os.path.join(output_path, 'Failed.txt')):
            time.sleep(1)
            self.update_progress(output_path)
        if os.path.exists(os.path.join(output_path, 'Completed.txt')):
            self.import_RT = True
            set_progress('Importing RT Structures')
        return None

    def importRT(self, exam):
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        file_path = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Output',
                                 self.patient.PatientID, SeriesUID)
        try:
            self.patient.ImportDicomDataFromPath(Path=file_path, CaseName=self.case.CaseName, SeriesFilter={},
                                                 ImportFilters=[])
        except:
            pi = self.patient_db.QueryPatientsFromPath(Path=file_path, SearchCriterias={'PatientID': self.patient.PatientID})[0]
            studies = self.patient_db.QueryStudiesFromPath(Path=file_path, SearchCriterias=pi)
            series = []
            for study in studies:
                series += self.patient_db.QuerySeriesFromPath(Path=file_path,
                                                              SearchCriterias=study)
            self.patient.ImportDataFromPath(Path=file_path, CaseName=self.case.CaseName,
                                            SeriesOrInstances=series, AllowMismatchingPatientID=True)
        return None

    def cleanout_folder(self, exam):
        data = exam.GetAcquisitionDataFromDicom()
        SeriesUID = data['SeriesModule']['SeriesInstanceUID']
        dicom_dir = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Output', self.patient.PatientID, SeriesUID)
        print('Cleaning up: Removing imported DICOMs, please check output folder for result')
        if os.path.exists(dicom_dir):
            files = [i for i in os.listdir(dicom_dir) if not i.startswith('user_')]
            for file in files:
                os.remove(os.path.join(dicom_dir, file))
            un = getpass.getuser()
            fid = open(os.path.join(dicom_dir, 'user_{}.txt'.format(un)), 'w+')
            fid.close()
        return None


if __name__ == "__main__":
    class_struct = create_RT_Structure(roi_name='Liver')
    class_struct.create_RT_Liver(class_struct.exam)
