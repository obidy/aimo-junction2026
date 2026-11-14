"""External agent entry point for one complete recipe basket."""
import argparse
import json
import os
import sys
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request',help='E.g. spaghetti bolognese for 200 people')
    parser.add_argument('--portions',type=int,default=200)
    parser.add_argument('--date',required=True)
    parser.add_argument('--preferences',default='')
    parser.add_argument('--automatic',action='store_true',help='Requires buyer-enabled server autonomy; mock commit only within whole-basket authority')
    args=parser.parse_args()
    token=os.environ.get('AIMO_AGENT_TOKEN','').strip()
    if not token:parser.error('Set the actual AIMO_AGENT_TOKEN printed by the running gateway.')
    try:
        with httpx.Client(base_url=os.environ.get('AIMO_GATEWAY_URL','http://127.0.0.1:8000'),timeout=660,
                          headers={'Authorization':'Bearer '+token}) as client:
            response=client.post('/recipe-plans',json={'request':args.request,'portions':args.portions,
                'delivery_date':args.date,'preferences':args.preferences,'autonomy':'automatic' if args.automatic else 'review',
                'auto_commit':args.automatic})
        if not response.is_success:
            print('Gateway HTTP',response.status_code,response.text);return 1
        p=response.json()
        print(p['id'],'|',p['recipe']['title'],'|',p['status'])
        print('Recipe source:',p['recipe']['source_url'])
        for row in p['ingredients']:
            print(row['name'],':',row['required_quantity'] or 'Unknown',row['unit'],'→',row['selected_name'] or row['status'])
        print('Combined subtotal including tax:',p['total_gross_eur'] or 'INCOMPLETE','EUR')
        for issue in p['issues']:print('BLOCKED:',issue)
        if p['mock_order']:print('Mock receipt:',p['mock_order']['id'],'— no supplier order sent.')
        else:print('Review the whole meal under Plan a meal → Recent meal plans in the dashboard.')
        return 0
    except httpx.RequestError as exc:
        print('Gateway connection failed:',type(exc).__name__);return 1


if __name__=='__main__':sys.exit(main())
