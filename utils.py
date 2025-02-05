import asana
from asana.rest import ApiException

def get_action_inputs(asana_pat: str):
    configuration = asana.Configuration()
    configuration.access_token = asana_pat
    api_client = asana.ApiClient(configuration)
    
    try:
        print("\n################## WORKSPACES ##################")
        
        workspaces = asana.WorkspacesApi(api_client).get_workspaces({
            "opt_fields": "name"
        })

        for workspace in workspaces:
            projects = asana.ProjectsApi(api_client).get_projects_for_workspace(workspace["gid"], {
                "opt_fields": "name"
            })
            
            print("\nWORKSPACE:\n" + "ID: " + workspace["gid"] + "\nName: " + workspace["name"]) 
            print("\n################## PROJECTS ##################")

            for project in projects:
                print("ID: " + project['gid'])
                print("Name: " + project['name'])

                print("\n################## TAGS ##################")

                tags = asana.SectionsApi(api_client).get_sections_for_project(project['gid'], {
                    "opt_fields": "name"
                })

                for tag in tags:
                    print("ID: " + tag['gid'])
                    print("Name: " + tag['name'])
                    print('-' * 50)

                print("\n################## CUSTOM FIELD STATUS ##################")

                custom_fields = asana.CustomFieldSettingsApi(api_client).get_custom_field_settings_for_project(project['gid'], {
                    "opt_fields": "custom_field.enum_options.name,custom_field.name"
                })

                for custom_field in custom_fields:
                    if custom_field['custom_field']['name'] == 'Status':
                        print("Status ID: " + custom_field['gid'], "\n")

                        for enum_option in custom_field['custom_field']['enum_options']:
                            print("Enum ID: " + enum_option['gid'])
                            print("Enum Name: " + enum_option['name'])
                            print('-' * 50)
                
                print()

            print()
    except ApiException as e:
        print("Exception when calling Asana API: %s\n" % e)
    
    

asana_pat = input("Enter your Asana Personal Access Token: ")
get_action_inputs(asana_pat)