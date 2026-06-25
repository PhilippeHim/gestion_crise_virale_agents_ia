from pipeline.pipeline import PipelineAgentX
import warnings
warnings.filterwarnings("ignore")


pipe = PipelineAgentX()

pipe.run("data_source/data.xlsx")