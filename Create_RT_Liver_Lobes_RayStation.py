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
    
        def check_contours(self, exam):
        actual_roi_names = ['Liver_Segment_{}_For_Sireesha'.format(i) for i in range(1, 5)]
        self.has_contours = True
        for actual_roi_name in actual_roi_names:
            set_progress('Checking to see if {} already has contours'.format(actual_roi_name))
            if actual_roi_name in self.rois_in_case:
                if not self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[actual_roi_name].HasContours():
                    self.has_contours = False
                    break
            else:
                self.has_contours = False
                break
        has_liver = False
        for actual_roi_name in ['Liver','Liver_BMA_Program_4']:
            if actual_roi_name in self.rois_in_case:
                if self.case.PatientModel.StructureSets[exam.Name].RoiGeometries[actual_roi_name].HasContours():
                    has_liver = True
                    break
        if not has_liver:
            print('You need a contour named Liver or Liver_BMA_Program_4')
            self.has_contours = True
    
    def create_RT_Liver(self, exam):
        self.export(exam)
        if not self.has_contours:
            self.import_data(exam)
        else:
            print('Already has contours defined')

    def export(self, exam):
        roi_name = self.roi_name
        roi_name += '_Auto_Contour'
        self.MRN = self.patient.PatientID
        self.base_path = '\\\\mymdafiles\\ou-radonc\\Raystation\\Clinical\\Auto_Contour_Sites\\'
        try:
            os.listdir(self.base_path)
        except:
            self.base_path = '\\\\mymdafiles\\ou-radonc\\Raystation\\Research\\Auto_Contour_Sites\\'
        #if not check_any_contours(case,exam): Doesn't work the way I want it to
        self.path = os.path.join(self.base_path,roi_name,'Input_3',self.MRN)
        self.rois_in_case = []
        for roi in self.case.PatientModel.RegionsOfInterest:
            self.rois_in_case.append(roi.Name)
        self.patient.Save()
        self.check_contours(exam=exam)
        if self.has_contours:
            return None
        self.patient.Save()
        self.cleanout_folder(exam)
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
        print(export_path)
        set_progress('Exporting dicom series')
        if not os.path.exists(os.path.join(export_path,'Completed.txt')):
            self.case.ScriptableDicomExport(ExportFolderPath=export_path, Examinations=[exam.Name],
                                            RtStructureSetsForExaminations=[exam.Name])
            fid = open(os.path.join(export_path,'Completed.txt'),'w+')
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
        dicom_dir = os.path.join(self.base_path, self.roi_name + '_Auto_Contour', 'Output', self.patient.PatientID,
                                 SeriesUID)
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
    class_struct = create_RT_Structure(roi_name='Liver_Segments')
    class_struct.create_RT_Liver(class_struct.exam)
