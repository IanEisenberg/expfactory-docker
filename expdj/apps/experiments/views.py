from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from expdj.apps.experiments.models import Experiment, Battery
from expdj.apps.experiments.forms import ExperimentForm, BatteryForm
from expdj.apps.experiments.utils import get_experiment_selection, install_experiments
from expdj.settings import BASE_DIR,STATIC_ROOT,MEDIA_ROOT
from expfactory.views import embed_experiment
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import shutil
import uuid
import json
import csv
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)

### AUTHENTICATION ####################################################

def owner_or_contrib(request,assessment):
    if not request.user.is_anonymous():
        if owner_or_super(request,assessment) or request.user in assessment.contributors.all():
            return True
    return False

def owner_or_super(request,assessment):
    if not request.user.is_anonymous():
        if assessment.owner == request.user or request.user.is_superuser:
            return True
    return False

def check_experiment_edit_permission(request):
    if request.user.is_superuser:
        return True
    return False

def check_battery_edit_permission(request):
    if not request.user.is_anonymous():
        #TODO: Add in check for battery owner here
        if request.user.is_superuser:
            return True
    return False

def is_question_editor(request):
    if not request.user.is_anonymous():   
        if request.user.is_superuser:
            return True
    return False           

def is_behavior_editor(request):
    if request.user.is_superuser:
        return True
    return False           


#### GETS #############################################################

# get experiment
@login_required
def get_experiment(eid,request,mode=None):
    keyargs = {'pk':eid}
    try:
        experiment = Experiment.objects.get(**keyargs)
    except Experiment.DoesNotExist:
        raise Http404
    else:
        return experiment


# get experiment
@login_required
def get_battery(bid,request,mode=None):
    keyargs = {'pk':bid}
    try:
        battery = Battery.objects.get(**keyargs)
    except Battery.DoesNotExist:
        raise Http404
    else:
        return battery


#### VIEWS #############################################################

# View a single experiment
@login_required
def view_experiment(request, eid):
    experiment = get_experiment(eid,request)
    
    # Determine permissions for edit and deletion
    edit_permission = check_experiment_edit_permission(request)
    delete_permission = check_experiment_edit_permission(request)

    context = {'experiment': experiment,
               'edit_permission':edit_permission,
               'delete_permission':delete_permission}

    return render_to_response('experiment_details.html', context)

# View a battery
@login_required
def view_battery(request, bid):
    battery = get_battery(bid,request)
    
    # Determine permissions for edit and deletion
    edit_permission = check_battery_edit_permission(request)
    delete_permission = check_battery_edit_permission(request)

    context = {'battery': battery,
               'edit_permission':edit_permission,
               'delete_permission':delete_permission}

    return render(request,'battery_details.html', context)

# All experiments
@login_required
def experiments_view(request):
    experiments = Experiment.objects.all()
    delete_permission = check_experiment_edit_permission(request)
    context = {'experiments': experiments,
               'delete_permission':delete_permission}
    return render(request, 'all_experiments.html', context)


# All batteries
@login_required
def batteries_view(request):
    batteries = Battery.objects.all()
    context = {'batteries': batteries}
    return render(request, 'all_batteries.html', context)


# Previews -------------------------------------------------------------
# Preview experiments
@login_required
def preview_experiment(request,eid):
    experiment = get_experiment(eid,request)
    experiment_folder = os.path.join(media_dir,"experiments",experiment.tag)    
    experiment_html = embed_experiment(experiment_folder,url_prefix="/")
    return render_to_response('experiment_preview.html', {"preview_html":experiment_html})

# Preview battery
@login_required
def preview_battery(request,bid):
    battery = get_battery(bid,request)
    # TODO: write function to generate battery and preview
    return render_to_response('battery_preview.html', {"preview_html":""})


#### EDIT/ADD/DELETE ###################################################

# Experiments ----------------------------------------------------------

@login_required
def add_experiment(request):
    '''add_experiment
    View for presenting available experiments to user (from expfactory-experiements repo)
    '''
    experiment_selection = get_experiment_selection()
    current_experiments = [x.tag for x in Experiment.objects.all()]
    experiments = [e for e in experiment_selection if e["tag"] not in current_experiments]
    context = {"newexperiments": experiments,
               "experiments": current_experiments}
    return render(request, "add_experiment.html", context)

@login_required
def add_experiments(request):
    '''add_experiments
    view for actually adding new experiments (files, etc) to application and database
    '''
    newexperiments = request.POST.keys()
    experiment_selection = get_experiment_selection()
    selected_experiments = [e["tag"] for e in experiment_selection if e["tag"] in newexperiments]
    errored_experiments = install_experiments(experiment_tags=selected_experiments)
    if len(errored_experiments) > 0:
        message = "The experiments %s did not install successfully." %(",".join(errored_experiments))
    else:
        message = "Experiments installed successfully."
    experiments = Experiment.objects.all()
    context = {"experiments":experiments,
               "message":message}
    return render(request, "all_experiments.html", context)

@login_required
def edit_experiment(request,eid=None):
    '''edit_experiment
    view for editing a single experiment. Likely only will be useful to change publication status
    '''

    # Editing an existing experiment
    if eid:
        experiment = get_experiment(eid,request)
    else:
        return HttpResponseRedirect("add_experiment")

    if request.method == "POST":
        form = ExperimentForm(request.POST, instance=experiment)

        if form.is_valid():
            experiment = form.save(commit=False)
            experiment.save()

            context = {
                'experiment': experiment.name,
            }
            return HttpResponseRedirect(experiment.get_absolute_url())
    else:
        form = ExperimentForm(instance=experiment)

    context = {"form": form,
               "experiment":experiment}
    return render(request, "edit_experiment.html", context)

# Delete an experiment
@login_required
def delete_experiment(request, eid):
    experiment = get_experiment(eid,request)
    if check_experiment_edit_permission(request):
        # Static Files
        static_files_dir = os.path.join(static_dir,experiment[0]["tag"])
        shutil.rmtree(static_files_dir)
        # Cognitive Atlas Task
        task = exp.cognitive_atlas_task
        if exp.cognitive_atlas_task.experiment_set.count() == 1:
            # We might want to delete concepts too? Ok for now.
            task.delete() 
        experiment.delete()
    return redirect('experiments')


# Battery --------------------------------------------------------------

@login_required
def add_battery(request):
    '''add_battery
    Function for adding new battery to database
    '''
    return redirect('batteries')

@login_required
def edit_battery(request, bid=None):
    header_text = "Add new battery"
    if bid:
        battery = get_battery(bid,request)
        is_owner = battery.owner == request.user
        header_text = battery.name 
        if not request.user.has_perm('battery.edit_battery', battery):
            return HttpResponseForbidden()
    else:
        is_owner = True
        battery = Battery(owner=request.user)
    if request.method == "POST":
        if is_owner:
            form = BatteryForm(request.POST,instance=battery)
        if form.is_valid():
            previous_contribs = set()
            if form.instance.pk is not None:
                previous_contribs = set(form.instance.contributors.all())
            battery = form.save(commit=False)
            battery.save()

            if is_owner:
                form.save_m2m()  # save contributors
                current_contribs = set(battery.contributors.all())
                new_contribs = list(current_contribs.difference(previous_contribs))

            return HttpResponseRedirect(battery.get_absolute_url())
    else:
        if is_owner:
            form = BatteryForm(instance=battery)
        else:
            form = BatteryForm(instance=battery)

    context = {"form": form, 
               "is_owner": is_owner,
               "header_text":header_text}

    return render(request, "edit_battery.html", context)


# Delete a battery
@login_required
def delete_battery(request, bid):
    battery = get_battery(bid,request)
    if request.user.has_perm('battery.delete_battery', battery):
        battery.delete()
    return redirect('batteries')



#### EXPORT #############################################################

# Export specific experiment data
@login_required
def export_battery(request,bid):
    battery = get_battery(bid,request)
    output_name = "%s.tsv" %(battery.id)
    print "WRITEME"


# Export specific experiment data
@login_required
def export_experiment(request,eid):
    experiment = get_experiment(eid,request)
    output_name = "%s.tsv" %(experiment.tag)
    return export_experiments([experiment],output_name)
   
# General function to export some number of experiments
@login_required
def export_experiments(experiments,output_name):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' %(output_name)
    writer = csv.writer(response,delimiter='\t')

    #TODO: update this for exports
    # Write header 
    writer.writerow(['experiment_name',
                     'experiment_tag',
                     'experiment_cognitive_atlas_task',
                     'experiment_cognitive_atlas_task_id',
                     'experiment_reference'])

    for experiment in experiments:
        try:
            writer.writerow([experiment.name,
                             experiment.tag,
                             experiment.cognitive_atlas_task,
                             experiment.cognitive_atlas_task_id,
                             experiment.reference])
        except:
            pass

    return response