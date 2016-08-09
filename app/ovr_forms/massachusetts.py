from base_ovr_form import BaseOVRForm, OVRError
from form_utils import get_address_components, options_dict, split_date, get_party_from_list


class Massachusetts(BaseOVRForm):

    def __init__(self):
        super(Massachusetts, self).__init__('https://www.sec.state.ma.us/OVR/Pages/MinRequirements.aspx?RMVId=True')
        self.add_required_fields(['will_be_18', 'legal_resident', 'consent_use_signature',
            'political_party', 'not_under_guardianship', 'disenfranchised'])

    def parse_errors(self):
        if self.errors:
            return self.errors

        messages = []
        for error in self.browser.select('.ErrorMessage li'):
            messages.append({'error': error.text})
        return messages

    def submit(self, user):

        self.validate(user)

        # format is: [kwargs to select / identify form, method to call with form]
        # frustratingly, MA uses the same methods and IDs for each form...
        forms = [
            [{'action': "./MinRequirements.aspx?RMVId=True"}, self.minimum_requirements],
            [{'action': "./FormAndReview.aspx?RMVId=True"}, self.rmv_identification],
            [{'action': "./FormAndReview.aspx?RMVId=True"}, self.complete_form],
            [{'action': "./FormAndReview.aspx?RMVId=True"}, self.review]
        ]

        for form_kwargs, handler in forms:

            step_form = self.browser.get_form(**form_kwargs)

            if step_form:
                handler(user, step_form)

            errors = self.parse_errors()

            if errors or not step_form:
                return {'errors': errors}

        return {'status': 'OK'}

    def minimum_requirements(self, user, form):

        if user['us_citizen']:
            form['ctl00$MainContent$ChkCitizen'].checked = 'checked'
            form['ctl00$MainContent$ChkCitizen'].value = 'on'

        else:
            self.add_error('You must be a U.S. Citizen.', field='us_citizen')

        if user['will_be_18']:
            form['ctl00$MainContent$ChkAge'].checked = 'checked'
            form['ctl00$MainContent$ChkAge'].value = 'on'

        else:
            self.add_error('You must be 18 by Election Day.', field='will_be_18')

        if user['legal_resident']:
            form['ctl00$MainContent$ChkResident'].checked = 'checked'
            form['ctl00$MainContent$ChkResident'].value = 'on'

        else:
            self.add_error('You must be a Massachusetts resident.', field='legal_resident')

        self.browser.submit_form(form, submit=form['ctl00$MainContent$BtnBeginOVR'])

        # if 'You must meet all 3 requirements' in self.browser.response.text:
        #     self.add_error('You must meet all three requirements: you are a U.S. citizen, you will be 18 on or before Election Day, and you are a Massachusetts resident')

    def rmv_identification(self, user, form):
        form['ctl00$MainContent$TxtFirstName'].value = user['first_name']
        form['ctl00$MainContent$TxtLastName'].value = user['last_name']

        (year, month, day) = split_date(user['date_of_birth'])
        form['ctl00$MainContent$TxtDoB'].value = '/'.join([month, day, year])

        form['ctl00$MainContent$TxtRMVID'].value = user['state_id_number']
        
        if user['consent_use_signature']:
            form['ctl00$MainContent$ChkConsent'].checked = 'checked'
            form['ctl00$MainContent$ChkConsent'].value = 'on'

        else:
            self.add_error("You must consent to using your signature from the Massachusetts RMV.", field='consent_use_signature')

        self.browser.submit_form(form, submit=form['ctl00$MainContent$BtnValidate'])

        if "Your RMV ID cannot be verified" in self.browser.response.text:
            self.add_error("Your Massachusetts RMV ID cannot be verified.", field='state_id_number')
            # todo: fall back to PDF form here? retry?

    def complete_form(self, user, form):

        address_components = get_address_components(user['address'], user['city'], user['state'], user['zip'])

        form['ctl00$MainContent$txtStNum'].value = address_components['primary_number']
        form['ctl00$MainContent$txStNameSuffix'].value = address_components['street_name']

        # todo: these two seem fraught for IndexErrors
        form['ctl00$MainContent$ddlStreetSuffix'].value = options_dict(form['ctl00$MainContent$ddlStreetSuffix'])[address_components['street_suffix'].upper()]
        form['ctl00$MainContent$ddlCityTown'].value = options_dict(form['ctl00$MainContent$ddlCityTown'])[user['city']]

        form['ctl00$MainContent$txtZip'].value = user['zip']

        user_party = user['political_party']
        parties = options_dict(form['ctl00$MainContent$ddlPartyList'])
        designations = options_dict(form['ctl00$MainContent$ddlPoliticalDesig'])

        party = get_party_from_list(user_party, parties.keys())
        designation = get_party_from_list(user_party, designations.keys())

        if user_party and user_party.lower().strip() != 'independent':

            if party:
                form['ctl00$MainContent$PartyEnrolled'].value = 'rdoBtnParty'
                # crucial - un-disable the party list
                del self.browser.select('select[name="ctl00$MainContent$ddlPartyList"]')[0]['disabled']
                form['ctl00$MainContent$ddlPartyList'].value = parties[party]

            elif designation:
                form['ctl00$MainContent$PartyEnrolled'].value = 'rdoBtnPolDesig'
                # crucial - un-disable the designation list
                del self.browser.select('select[name="ctl00$MainContent$ddlPoliticalDesig"]')[0]['disabled']
                form['ctl00$MainContent$ddlPoliticalDesig'].value = designations[designation]
            
        else:
            # No Party (Unenrolled, commonly referred to as ''Independent'')
            form['ctl00$MainContent$PartyEnrolled'].value = 'rdoBtnNoParty'
        

        # possible todos, all optional:
        # former name
        # separate mailing address
        # phone number
        # address where you were last registered to vote.

        self.browser.submit_form(form)

    def review(self, user, form):

        # I hereby swear (affirm) that I am the person named above, that the
        # above information is true, that I AM A CITIZEN OF THE UNITED STATES,
        # that I am not a person under guardianship which prohibits my
        # registering to vote, that I am not temporarily or permanantly
        # disqualified by law from voting because of corrupt practices in
        # respect to elections, that I am not currently incarcerated for a
        # felony conviction, and that I consider this residence to be my home.

        if user['us_citizen'] and user['legal_resident'] \
            and not (user['disqualified'] or user['disenfranchised']):

            form['ctl00$MainContent$ChkIsSwear'].checked = 'checked'
            form['ctl00$MainContent$ChkIsSwear'].value = 'on'

        elif not user['us_citizen']:
            self.add_error("You must be a U.S. Citizen.", field='us_citizen')

        elif not user['not_a_felon']:
            self.add_error("You must not be a felon.", field='not_a_felon')

        elif not user['legal_resident']:
            self.add_error("You must be a Massachusetts resident.", field='legal_resident')

        elif user['disenfranchised']:
            self.add_error("You may not register to vote if you are currently imprisoned or on parole for the conviction of a felony.", field='disenfranchised')

        elif user['disqualified']:
            self.add_error("You must not be legally disqualified to vote, or under legal guardianship which prohibits your registering. ", field='disqualified')

